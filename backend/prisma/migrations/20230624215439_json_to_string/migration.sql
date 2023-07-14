-- AlterTable
ALTER TABLE "CachedCourseInfo" ALTER COLUMN "info" SET DATA TYPE TEXT;

-- AlterTable
ALTER TABLE "Course" ALTER COLUMN "deps" SET DATA TYPE TEXT;

-- AlterTable
ALTER TABLE "Curriculum" ALTER COLUMN "curriculum" SET DATA TYPE TEXT;

-- AlterTable
ALTER TABLE "Plan" ALTER COLUMN "validatable_plan" SET DATA TYPE TEXT;
