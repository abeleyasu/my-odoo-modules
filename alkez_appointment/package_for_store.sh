#!/bin/bash
# Package Appointment module for Odoo App Store
# Author: Abel Eyasu - Alkez ERP

set -e

MODULE_NAME="appointment"
VERSION="18.0.1.3.1"
OUTPUT_DIR="/opt/odoo"
ADDONS_DIR="/opt/odoo/custom_addons"

echo "==================================="
echo "Packaging Appointment for Odoo App Store"
echo "Version: $VERSION"
echo "==================================="

# Navigate to addons directory
cd "$ADDONS_DIR"

# Clean up any previous package
rm -f "$OUTPUT_DIR/${MODULE_NAME}-${VERSION}.zip"

# Create the zip package
echo "Creating package..."
zip -r "$OUTPUT_DIR/${MODULE_NAME}-${VERSION}.zip" \
    "$MODULE_NAME/" \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.git*" \
    -x "*.DS_Store" \
    -x "*~" \
    -x "*.bak"

echo ""
echo "==================================="
echo "Package created successfully!"
echo "Location: $OUTPUT_DIR/${MODULE_NAME}-${VERSION}.zip"
echo "==================================="

# Show package info
ls -lh "$OUTPUT_DIR/${MODULE_NAME}-${VERSION}.zip"

echo ""
echo "Ready for upload to Odoo App Store!"
echo ""
echo "Upload checklist:"
echo "  ✓ Module name: Appointment"
echo "  ✓ Version: $VERSION"
echo "  ✓ License: OPL-1"
echo "  ✓ Price: \$100"
echo "  ✓ Author: Abel Eyasu"
echo "  ✓ Icon: static/description/icon.png"
echo "  ✓ Banner: static/description/banner.png"
echo "  ✓ Description: static/description/index.html"
