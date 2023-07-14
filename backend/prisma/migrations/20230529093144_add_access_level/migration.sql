-- CreateTable
CREATE TABLE "AccessLevel" (
    "user_rut" TEXT NOT NULL,
    "is_mod" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AccessLevel_pkey" PRIMARY KEY ("user_rut")
);
