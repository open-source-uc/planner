-- CreateTable
CREATE TABLE "Equivalence" (
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "is_homogeneous" BOOLEAN NOT NULL,
    "courses" TEXT[],

    CONSTRAINT "Equivalence_pkey" PRIMARY KEY ("code")
);
