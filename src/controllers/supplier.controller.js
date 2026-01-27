import prisma from "../prisma.js";

/**
 * GET /api/suppliers/me
 * Récupérer le profil fournisseur du user connecté
 */
export const getMySupplierProfile = async (req, res) => {
  try {
    const userId = req.user.id;

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
 * POST /api/suppliers/profile
 * Création du profil fournisseur
 */
/**
 * POST /api/suppliers/profile
 * Création du profil fournisseur
 */
export const createSupplierProfile = async (req, res) => {
  try {
    const userId = req.user.id;

    const {
      companyName,
      companyAddress,
      nif,
      nrc,
      contactName,
      contactPhone,
    } = req.body;

    // Champs obligatoires EXACTEMENT selon Prisma
    if (
      !companyName ||
      !companyAddress ||
      !nif ||
      !nrc ||
      !contactName ||
      !contactPhone
    ) {
      return res.status(400).json({
        message: "Champs obligatoires manquants",
      });
    }

    const existingSupplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (existingSupplier) {
      return res.status(400).json({
        message: "Profil fournisseur déjà existant",
      });
    }

    const supplier = await prisma.supplier.create({
      data: {
        companyName,
        companyAddress,
        nif,
        nrc,
        contactName,
        contactPhone,
        userId,
        status: "PENDING",
      },
    });

    res.status(201).json(supplier);
  } catch (error) {
    console.error("CREATE SUPPLIER ERROR:", error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};


/**
 * PUT /api/suppliers/orders/:id/status
 * Mise à jour du statut d’une commande fournisseur
 */
export const updateOrderStatus = async (req, res) => {
  try {
    const userId = req.user.id;
    const { id } = req.params;
    const { status } = req.body;

    if (!status) {
      return res.status(400).json({ message: "Statut manquant" });
    }

    const supplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({ message: "Fournisseur non autorisé" });
    }

    const order = await prisma.order.findUnique({
      where: { id: Number(id) },
    });

    if (!order) {
      return res.status(404).json({ message: "Commande introuvable" });
    }

    if (order.supplierId !== supplier.id) {
      return res.status(403).json({ message: "Accès interdit" });
    }

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
