/*
  Warnings:

  - You are about to drop the column `name` on the `Supplier` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[userId]` on the table `Supplier` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `companyAddress` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `companyName` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `contactName` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `contactPhone` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `nif` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `nrc` to the `Supplier` table without a default value. This is not possible if the table is not empty.
  - Added the required column `userId` to the `Supplier` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Supplier" DROP COLUMN "name",
ADD COLUMN     "companyAddress" TEXT NOT NULL,
ADD COLUMN     "companyName" TEXT NOT NULL,
ADD COLUMN     "contactName" TEXT NOT NULL,
ADD COLUMN     "contactPhone" TEXT NOT NULL,
ADD COLUMN     "nif" TEXT NOT NULL,
ADD COLUMN     "nrc" TEXT NOT NULL,
ADD COLUMN     "userId" INTEGER NOT NULL,
ALTER COLUMN "status" SET DEFAULT 'PENDING';

-- CreateIndex
CREATE UNIQUE INDEX "Supplier_userId_key" ON "Supplier"("userId");

-- AddForeignKey
ALTER TABLE "Supplier" ADD CONSTRAINT "Supplier_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
