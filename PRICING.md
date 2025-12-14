# Pricing Information

## Overview

Both modules in this repository are **paid/proprietary modules** licensed under OPL-1 (Odoo Proprietary License). They are ready for sale on the Odoo App Store.

## Module Pricing

### Office Document Creator
- **Price:** $250 USD
- **License:** OPL-1 (Odoo Proprietary License)
- **Type:** One-time payment
- **Includes:**
  - Lifetime license for your organization
  - Free updates and bug fixes
  - Email support
  - Unlimited Odoo instances within your organization
  - All features: Document creation, ONLYOFFICE integration, folder organization, sharing, trash & restore

### O-Meet (Jitsi)
- **Price:** $200 USD
- **License:** OPL-1 (Odoo Proprietary License)
- **Type:** One-time payment
- **Includes:**
  - Lifetime license for your organization
  - Free updates and bug fixes
  - Email support
  - Unlimited Odoo instances within your organization
  - All features: Instant meetings, scheduled meetings, calendar integration, JWT authentication

## Licensing Details

Both modules use the **Odoo Proprietary License v1.0 (OPL-1)**, which means:

1. **Purchase Required:** Users must purchase a license to use the software
2. **No Redistribution:** Cannot publish, distribute, sublicense, or sell copies
3. **Organizational Use:** License covers unlimited users and instances within the purchasing organization
4. **Module Development:** You can develop modules that use this software as a library
5. **No Source Code Copying:** Cannot copy source code or material from the software

## Setting Up Pricing on Odoo App Store

When publishing to the Odoo App Store:

1. **Repository Registration:**
   - URL format: `ssh://git@github.com/abeleyasu/my-odoo-modules#18.0`
   - Make repository public OR grant access to `online-odoo` user

2. **Module Configuration:**
   - The `price` and `currency` fields in `__manifest__.py` will be read by Odoo
   - The `license` field is set to `OPL-1`

3. **App Store Settings:**
   - During module registration, confirm the pricing shown matches the manifest
   - Set support options and contact information
   - Add payment/billing details for receiving payments

## Manifest Configuration

Both modules have been updated with the following keys in their `__manifest__.py`:

```python
'license': 'OPL-1',
'price': 250.00,  # or 200.00 for jitsi_meet_ui
'currency': 'USD',
```

These fields are automatically detected by the Odoo App Store and used to:
- Display the price to potential buyers
- Handle the payment process
- Generate licenses for purchasers

## Support and Updates

With the purchase of either module, customers receive:

- **Email Support:** Technical assistance via email
- **Bug Fixes:** Free bug fixes for the lifetime of the module
- **Updates:** Free updates including new features and improvements
- **Documentation:** Comprehensive documentation included

## Notes

- Prices are subject to change
- One-time payment model (no recurring fees)
- Covers unlimited users within the purchasing organization
- Works with Odoo Community Edition (no Enterprise license required)
- Compatible with Odoo 18.0

## Questions?

For questions about pricing, licensing, or bulk purchases, please contact the module author via the Odoo App Store messaging system.
