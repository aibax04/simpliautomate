# Implementation Plan - Logo Overlay Feature

The goal is to allow users to have their uploaded product logo automatically overlaid on the bottom right of generated images.

## Proposed Changes

### Backend - Agents

#### [MODIFY] [post_generation_agent.py](file:///c:/Users/mohda/OneDrive/Desktop/simplii/backend/agents/post_generation_agent.py)
- Update `generate` method to extract `logo_path` from `product_info['collateral']` if available.
- Look for `file_type == 'logo'` or check filenames for 'logo'.
- Pass this `logo_path` into `visual_plan`.

#### [MODIFY] [visual_planning_agent.py](file:///c:/Users/mohda/OneDrive/Desktop/simplii/backend/agents/visual_planning_agent.py)
- Ensure `plan_visual` passes the `logo_path` through to the returned JSON structure (so `ImageAgent` can read it).

#### [MODIFY] [image_agent.py](file:///c:/Users/mohda/OneDrive/Desktop/simplii/backend/agents/image_agent.py)
- Add a new helper method `_overlay_logo(self, main_image_path, logo_path)`.
    - Logic: Open images, resize logo to ~15-20% of main image width, paste at bottom-right with padding.
- Call this method at the end of `generate_image` if `visual_plan` contains a `logo_path`.
- Ensure it handles transparency (RGBA).

## Verification Plan

### Manual Verification
1.  **Upload a Logo**: Use the Product UI (if available) or manually add a `ProductCollateral` entry with `file_type='logo'` in the DB (or rename a file in `uploads/collateral` and hack the local state to test).
2.  **Trigger Generation**: Run a generation task (e.g., via `python run.py` and curl or UI).
3.  **Inspect Output**: Check `frontend/generated_images/` to see if the new image has the logo overlay.
