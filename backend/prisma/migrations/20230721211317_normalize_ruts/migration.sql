-- Remove leading zeros from RUTs.

UPDATE "AccessLevel"
SET user_rut = TRIM(LEADING '0' FROM user_rut);

UPDATE "Plan"
SET user_rut = TRIM(LEADING '0' FROM user_rut);
