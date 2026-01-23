import prisma from "../prisma.js";

/**
 * 🔐 Création d’un produit (fournisseur connecté)
 */
export const createProduct = async (req, res) => {
  const userId = req.user.userId;
  const { name, description, price, stock } = req.body;

  if (!name || !price || stock === undefined) {
    return res.status(400).json({ message: "Données produit invalides" });
  }

  try {
    // 🔎 Trouver le supplier lié à l'utilisateur
    const supplier = await prisma.supplier.findUnique({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({ message: "Fournisseur introuvable" });
    }

    const product = await prisma.product.create({
      data: {
        name,
        description,
        price,
        stock,
        isActive: true,
        supplierId: supplier.id,
      },
    });

    res.status(201).json(product);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur création produit" });
  }
};

/**
 * 📦 Récupérer les produits du fournisseur connecté
 */
export const getMyProducts = async (req, res) => {
  const userId = req.user.userId;

  try {
    const supplier = await prisma.supplier.findUnique({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({ message: "Fournisseur introuvable" });
    }

    const products = await prisma.product.findMany({
      where: { supplierId: supplier.id },
    });

    res.json(products);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Erreur récupération produits" });
  }
};
