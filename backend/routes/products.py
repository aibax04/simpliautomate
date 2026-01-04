from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.db.database import get_db
from backend.db.models import User, Product, ProductCollateral
from backend.auth.security import get_current_user
import os
import uuid
from typing import List, Optional

router = APIRouter(prefix="/products", tags=["products"])

UPLOAD_DIR = "uploads/collateral"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    product = Product(user_id=user.id, name=name, description=description)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.get("")
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(Product).where(Product.user_id == user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = delete(Product).where(Product.id == product_id, Product.user_id == user.id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "success"}

@router.post("/{product_id}/collateral")
async def upload_collateral(
    product_id: int,
    file: UploadFile = File(...),
    file_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Verify product ownership
    stmt = select(Product).where(Product.id == product_id, Product.user_id == user.id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    collateral = ProductCollateral(
        product_id=product_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type
    )
    db.add(collateral)
    await db.commit()
    await db.refresh(collateral)
    return collateral

@router.get("/{product_id}/collateral")
async def get_collateral(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Verify product ownership
    stmt = select(Product).where(Product.id == product_id, Product.user_id == user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    stmt = select(ProductCollateral).where(ProductCollateral.product_id == product_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.delete("/collateral/{collateral_id}")
async def delete_collateral(
    collateral_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Join with Product to check ownership
    stmt = select(ProductCollateral).join(Product).where(
        ProductCollateral.id == collateral_id,
        Product.user_id == user.id
    )
    result = await db.execute(stmt)
    collateral = result.scalar_one_or_none()
    if not collateral:
        raise HTTPException(status_code=404, detail="Collateral not found")

    if os.path.exists(collateral.file_path):
        os.remove(collateral.file_path)

    await db.delete(collateral)
    await db.commit()
    return {"status": "success"}
