import prisma from "../prisma.js";

/**
 * 👤 Profil du fournisseur connecté
 */
export const getMySupplierProfile = async (req, res) => {
  const userId = req.user.userId;

  try {
    const supplier = await prisma.supplier.findUnique({
      where: { userId },
      include: {
        user: {
          select: {
            id: true,
            email: true,
          },
        },
      },
    });

    if (!supplier) {
      return res.status(404).json({ message: "Fournisseur introuvable" });
    }

    res.json(supplier);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur fournisseur" });
  }
};

/**
 * 🔄 Mise à jour du statut d’une commande par le fournisseur
 */
export const updateOrderStatus = async (req, res) => {
  const userId = req.user.userId;
  const orderId = Number(req.params.id);
  const { status } = req.body;

  if (!status) {
    return res.status(400).json({ message: "Statut manquant" });
  }

  try {
    const supplier = await prisma.supplier.findUnique({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({ message: "Fournisseur introuvable" });
    }

    const order = await prisma.order.findFirst({
      where: {
        id: orderId,
        supplierId: supplier.id,
      },
    });

    if (!order) {
      return res.status(404).json({ message: "Commande introuvable" });
    }

    const updatedOrder = await prisma.order.update({
      where: { id: orderId },
      data: { status },
    });

    res.json(updatedOrder);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur mise à jour commande" });
  }
};
