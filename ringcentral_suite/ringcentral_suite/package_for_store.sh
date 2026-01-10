#!/bin/bash
# Package RingCentral Suite for Odoo App Store
# Author: Abel Eyasu - Alkez ERP

set -e

# Configuration
VERSION="18.0.1.0.0"
PACKAGE_NAME="ringcentral_suite-${VERSION}"
ADDONS_DIR="/opt/odoo/custom_addons"
OUTPUT_DIR="/opt/odoo"

# Modules to include
MODULES=(
    "ringcentral_base"
    "ringcentral_call"
    "ringcentral_sms"
    "ringcentral_webrtc"
    "ringcentral_recording"
    "ringcentral_ai"
    "ringcentral_voicemail"
    "ringcentral_fax"
    "ringcentral_presence"
    "ringcentral_meet"
    "ringcentral_portal"
    "ringcentral_website"
    "ringcentral_analytics"
    "ringcentral_compliance"
    "ringcentral_quality"
    "ringcentral_crm"
    "ringcentral_sale"
    "ringcentral_project"
    "ringcentral_helpdesk"
    "ringcentral_hr"
    "ringcentral_contact_center"
    "ringcentral_multiline"
    "ringcentral_suite"
)

echo "=============================================="
echo "  RingCentral Suite Packaging Script"
echo "  Version: ${VERSION}"
echo "=============================================="
echo ""

# Create temp directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/${PACKAGE_NAME}"
mkdir -p "${PACKAGE_DIR}"

echo "📦 Packaging modules..."
for module in "${MODULES[@]}"; do
    if [ -d "${ADDONS_DIR}/${module}" ]; then
        echo "  ✓ ${module}"
        cp -r "${ADDONS_DIR}/${module}" "${PACKAGE_DIR}/"
    else
        echo "  ✗ ${module} (not found)"
    fi
done

# Remove __pycache__ and .pyc files
echo ""
echo "🧹 Cleaning up cache files..."
find "${PACKAGE_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.pyo" -delete 2>/dev/null || true

# Create zip file
echo ""
echo "📁 Creating archive..."
cd "${TEMP_DIR}"
zip -r "${OUTPUT_DIR}/${PACKAGE_NAME}.zip" "${PACKAGE_NAME}" -x "*.git*"

# Cleanup
rm -rf "${TEMP_DIR}"

echo ""
echo "=============================================="
echo "  Package created successfully!"
echo "=============================================="
echo ""
echo "📍 Location: ${OUTPUT_DIR}/${PACKAGE_NAME}.zip"
echo ""
echo "📋 Next steps for Odoo App Store submission:"
echo "   1. Log in to https://apps.odoo.com/apps/dashboard"
echo "   2. Click 'Add an App'"
echo "   3. Upload: ${PACKAGE_NAME}.zip"
echo "   4. Set price: \$250.00"
echo "   5. Select Odoo version: 18.0"
echo "   6. Category: Phone/Telephony"
echo "   7. Submit for review"
echo ""
echo "💡 Make sure banner.png (800x320) and icon.png (96x96) look good!"
echo ""
