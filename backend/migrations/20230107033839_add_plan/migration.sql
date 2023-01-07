-- CreateTable
CREATE TABLE "Plan" (
    "id" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "name" TEXT NOT NULL,
    "user_rut" TEXT NOT NULL,
    "next_semester" INTEGER NOT NULL,
    "level" INTEGER,
    "school" TEXT,
    "program" TEXT,
    "career" TEXT,

    CONSTRAINT "Plan_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlanSemester" (
    "id" TEXT NOT NULL,
    "plan_id" TEXT NOT NULL,
    "number" INTEGER NOT NULL,

    CONSTRAINT "PlanSemester_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlanClass" (
    "id" TEXT NOT NULL,
    "semester_id" TEXT NOT NULL,
    "class_code" TEXT NOT NULL,

    CONSTRAINT "PlanClass_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "PlanSemester" ADD CONSTRAINT "PlanSemester_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "Plan"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlanClass" ADD CONSTRAINT "PlanClass_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "PlanSemester"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
