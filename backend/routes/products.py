from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.db.database import get_db
from backend.db.models import User, Product, ProductCollateral
from backend.auth.security import get_current_user
import os
import uuid
from typing import List, Optional

from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/products", tags=["products"])

UPLOAD_DIR = "uploads/collateral"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    documents: List[UploadFile] = File([]),
    photos: List[UploadFile] = File([]),
    logo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    product = Product(user_id=user.id, name=name, description=description, website_url=website_url)
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Handle Logo
    if logo and logo.filename:
        file_ext = os.path.splitext(logo.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as f:
            content = await logo.read()
            f.write(content)
        
        collateral = ProductCollateral(
            product_id=product.id,
            file_name="logo_" + logo.filename, # Prefix just in case
            file_path=file_path,
            file_type="logo"
        )
        db.add(collateral)

    # Handle Documents
    for doc in documents:
        if doc.filename:
            file_ext = os.path.splitext(doc.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as f:
                content = await doc.read()
                f.write(content)
            
            collateral = ProductCollateral(
                product_id=product.id,
                file_name=doc.filename,
                file_path=file_path,
                file_type="document"
            )
            db.add(collateral)

    # Handle Photos
    for photo in photos:
        if photo.filename:
            file_ext = os.path.splitext(photo.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as f:
                content = await photo.read()
                f.write(content)
            
            collateral = ProductCollateral(
                product_id=product.id,
                file_name=photo.filename,
                file_path=file_path,
                file_type="photo"
            )
            db.add(collateral)

    await db.commit()
    
    # Reload with collateral
    stmt = select(Product).where(Product.id == product.id).options(selectinload(Product.collateral))
    res = await db.execute(stmt)
    return res.scalar_one()

@router.get("")
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(Product).where(Product.user_id == user.id).options(selectinload(Product.collateral))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Fetch product with collateral to delete files
    stmt = select(Product).where(Product.id == product_id, Product.user_id == user.id).options(selectinload(Product.collateral))
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Delete physical files
    for collateral in product.collateral:
        if os.path.exists(collateral.file_path):
            try:
                os.remove(collateral.file_path)
            except Exception as e:
                print(f"Failed to delete file {collateral.file_path}: {e}")

    await db.delete(product)
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
