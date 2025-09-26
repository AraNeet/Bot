# Templates Directory

Place your reference icons/images here for corner-based visual verification.

## Required Corner Templates

The new corner-based detection system requires three specific template images:

### Primary Templates (Required)
- **notepad_icon.png**: Notepad icon from the top-left corner of the title bar
- **close_x.png**: Close X button from the top-right corner of the title bar  
- **bottom_right_element.png**: Any stable UI element from the bottom-right corner

### Legacy Template (Optional)
- **Icon.png**: General application icon for fallback verification

## Template Guidelines

### Capture Requirements
- Capture templates when the application is maximized and properly displayed
- Use the same display scale (DPI) as your runtime environment
- Save as PNG format to avoid compression artifacts
- Aim for small, focused regions (20-80 pixels on each side)

### Corner-Specific Guidelines

**Top-Left Corner (notepad_icon.png):**
- Focus on just the Notepad icon in the title bar
- Include minimal surrounding area
- Should be unique and high-contrast

**Top-Right Corner (close_x.png):**
- Capture the close X button and immediate area
- Ensure it's the actual close button, not minimize/maximize
- Include enough context to be unique

**Bottom-Right Corner (bottom_right_element.png):**
- Can be any stable UI element (status bar corner, scroll bar, etc.)
- Must be consistently present when application is maximized
- Should be visually distinct

## How Corner Detection Works

1. **Region Division**: Screen is divided into 200x200 pixel corner regions
2. **Template Matching**: Each template is searched only in its designated corner
3. **Maximization Detection**: Application is considered maximized when ALL three corner templates are found
4. **Fallback Support**: System falls back to legacy templates if corner templates aren't available

## Testing Your Templates

Use the test script to verify your templates work correctly:
```bash
python test_corner_matching.py
```

This will show you which templates are found and help debug any matching issues.
