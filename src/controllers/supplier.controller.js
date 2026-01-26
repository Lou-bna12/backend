import prisma from "../prisma.js";

/**
 * GET /api/suppliers/me
 */
export const getMySupplierProfile = async (req, res) => {
  try {
    const userId = req.user.userId;

    const supplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (!supplier) {
      return res
        .status(404)
        .json({ message: "Fournisseur non trouvé pour cet utilisateur" });
    }

    res.json(supplier);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};

/**
 * PUT /api/suppliers/orders/:id/status
 */
export const updateOrderStatus = async (req, res) => {
  const userId = req.user.userId;
  const { id } = req.params;
  const { status } = req.body;

  if (!status) {
    return res.status(400).json({ message: "Statut manquant" });
  }

  try {
    // 1️⃣ Récupérer le supplier lié au user
    const supplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({ message: "Fournisseur non autorisé" });
    }

    // 2️⃣ Récupérer la commande
    const order = await prisma.order.findUnique({
      where: { id: Number(id) },
    });

    if (!order) {
      return res.status(404).json({ message: "Commande introuvable" });
    }

    // 3️⃣ Vérifier que la commande appartient à ce fournisseur
    if (order.supplierId !== supplier.id) {
      return res.status(403).json({ message: "Accès interdit" });
    }

    // 4️⃣ Mise à jour du statut
    const updatedOrder = await prisma.order.update({
      where: { id: Number(id) },
      data: { status },
    });

    res.json(updatedOrder);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};
