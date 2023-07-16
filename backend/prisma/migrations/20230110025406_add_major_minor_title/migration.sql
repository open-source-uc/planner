-- CreateTable
CREATE TABLE "Major" (
    "cyear" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "version" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Minor" (
    "cyear" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "version" TEXT NOT NULL,
    "minor_type" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "MajorMinor" (
    "major" TEXT NOT NULL,
    "minor" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Title" (
    "cyear" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "version" TEXT NOT NULL,
    "title_type" TEXT NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "Major_cyear_code_key" ON "Major"("cyear", "code");

-- CreateIndex
CREATE UNIQUE INDEX "Minor_cyear_code_key" ON "Minor"("cyear", "code");

-- CreateIndex
CREATE UNIQUE INDEX "MajorMinor_major_minor_key" ON "MajorMinor"("major", "minor");

-- CreateIndex
CREATE UNIQUE INDEX "Title_cyear_code_key" ON "Title"("cyear", "code");
