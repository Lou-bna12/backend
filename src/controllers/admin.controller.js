import prisma from "../prisma.js";

export const getPendingSuppliers = async (req, res) => {
  const suppliers = await prisma.supplier.findMany({
    where: { status: "PENDING" },
    include: {
      user: {
        select: { id: true, email: true, name: true },
      },
    },
  });

  res.json(suppliers);
};

export const approveSupplier = async (req, res) => {
  const supplierId = Number(req.params.id);

  const supplier = await prisma.supplier.update({
    where: { id: supplierId },
    data: { status: "APPROVED" },
  });

  await prisma.user.update({
    where: { id: supplier.userId },
    data: { role: "SUPPLIER" },
  });

  res.json({ message: "Fournisseur approuvé" });
};

export const rejectSupplier = async (req, res) => {
  const supplierId = Number(req.params.id);

  await prisma.supplier.update({
    where: { id: supplierId },
    data: { status: "REJECTED" },
  });

  res.json({ message: "Fournisseur rejeté" });
};
