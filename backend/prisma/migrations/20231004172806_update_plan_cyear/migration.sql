-- Update the curriculum.cyear field
-- Do the operation `plan.curriculum.cyear = plan.curriculum.cyear.raw` for all plans.

UPDATE "Plan"
SET validatable_plan = jsonb_set(validatable_plan::jsonb, '{curriculum,cyear}', validatable_plan::jsonb -> 'curriculum' -> 'cyear' -> 'raw') #>> '{}';
