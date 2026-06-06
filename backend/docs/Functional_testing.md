Waiting for API server on port 8000 to be ready...
API is ready!

================================================================================
 1. USER REGISTRATION & LOGIN
================================================================================
Registered & Logged in Mumbai Patient (patient)
Registered & Logged in Navi Mumbai Donor (Near) (donor)
Registered & Logged in Pune Donor (Far) (donor)
Registered & Logged in Mumbai Incompatible Donor (donor)
Registered & Logged in Mumbai Blood Bank (blood_bank)
Registered & Logged in Coordinator User (coordinator)

================================================================================
 2. CREATING PROFILES (GEOLOCATION)
================================================================================
Mumbai Patient profile created successfully.
Compatible Near Donor profile created. Donor ID: 99
Compatible Far Donor profile created. Donor ID: 100
Incompatible Near Donor profile created.
Blood Bank profile created.

================================================================================
 3. INVENTORY, UNITS AND LAB QUALITY CONTROLS
================================================================================
Inventory set successfully (ID: 58, Qty: 1000ml O-).
Blood unit checked in successfully (ID: 23).
Blood unit quality validated (marked as safe/available).

================================================================================
 4. VALIDATION REPORTS & PDF SECURITY GUARD
================================================================================
Validation report submitted successfully (ID: 13).
PDF Lab report uploaded successfully by Blood Bank.
Success: Authorized donor successfully downloaded PDF.
Success: Authorized Blood Bank successfully downloaded PDF.
Success: Security Guard blocked unauthorized download attempt with 403.

================================================================================
 5. NEAREST BLOOD BANK LOCATOR
================================================================================
Success: Found nearest blood bank Mumbai Central at 0.0 Km distance.

================================================================================
 6. ML RANKING & GEOJSON MAP DATA
================================================================================
Success: ML Ranking predicted near donor with exact distance 16.68 km (match prob: 0.9331).
Success: GeoJSON Coordinator Map feature collection exported successfully.

================================================================================
 7. URGENT REQUEST (100 KM RADIUS FILTER & ACCEPTS)
================================================================================
Created critical urgent request (ID: 74).
Success: Radius broadcast logic correctly filtered notifications (Near Donor/Bank got alerts, Far/Incompatible did not).
Success: Far donor acceptance rejected by radius filter.
Success: Near compatible donor accepted request (status changed to accepted).

================================================================================
 8. NON-URGENT ROUTING (INVENTORY CHECKS & ML FALLBACK)
================================================================================
Test Case A: Stock is available in local blood bank...
Success: Non-urgent request created when stock exists.
Success: Patient received notification of available stock at nearby blood bank.
Test Case B: Stock is empty...
Success: Non-urgent request B- created (ID: 76).
Success: Blood Bank claimed the empty stock request successfully via accept-bank API.

================================================================================
 ALL SYSTEM FUNCTIONAL TESTS COMPLETED SUCCESSFULLY!
================================================================================
