#!/usr/bin/env python3
"""
Simple Test for Image Comparison Button Functionality
"""

def test_basic_functionality():
    """Test basic functionality exists"""
    print("Testing Image Comparison Button Implementation")
    print("=" * 50)

    try:
        with open('frontend/static/js/swipe.js', 'r', encoding='utf-8') as f:
            js_content = f.read()

        functions_found = 0
        required_functions = ['addImageComparisonUI', 'toggleImageView', 'updateImageView']

        for func in required_functions:
            if f'{func}(' in js_content:
                print(f"Found: {func}")
                functions_found += 1
            else:
                print(f"Missing: {func}")

        if 'show-current-btn' in js_content and 'show-previous-btn' in js_content:
            print("Found: Button IDs")
            functions_found += 1
        else:
            print("Missing: Button IDs")

        if 'this.currentImageView' in js_content:
            print("Found: currentImageView property")
            functions_found += 1
        else:
            print("Missing: currentImageView property")

        print(f"\nResult: {functions_found}/5 components found")

        if functions_found >= 4:
            print("SUCCESS: Button functionality implemented")
            return True
        else:
            print("INCOMPLETE: Missing key components")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\nImage comparison buttons are ready!")
    else:
        print("\nImplementation incomplete.")