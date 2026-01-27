import prisma from "../prisma.js";

export const createProduct = async (req, res) => {
  try {
    const userId = req.user.id;

    // Vérifier que l'utilisateur est fournisseur
    const supplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({
        message: "Profil fournisseur requis pour créer un produit",
      });
    }

    const { name, price, stock } = req.body;

    // Champs obligatoires EXACTS selon Prisma
    if (!name || price === undefined || stock === undefined) {
      return res.status(400).json({
        message: "Champs obligatoires manquants",
      });
    }

    const product = await prisma.product.create({
      data: {
        name,
        price,
        stock,
        supplierId: supplier.id,
      },
    });

    res.status(201).json(product);
  } catch (error) {
    console.error("CREATE PRODUCT ERROR:", error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};


/**
 * GET /api/products/me
 * Récupérer les produits du fournisseur connecté
 */
export const getMyProducts = async (req, res) => {
  try {
    const userId = req.user.id;

    const supplier = await prisma.supplier.findFirst({
      where: { userId },
    });

    if (!supplier) {
      return res.status(403).json({
        message: "Profil fournisseur requis",
      });
    }

    const products = await prisma.product.findMany({
      where: { supplierId: supplier.id },
      orderBy: { id: "desc" },
    });

    res.json(products);
  } catch (error) {
    console.error("GET MY PRODUCTS ERROR:", error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};

/**
 * GET /api/products
 * Récupérer tous les produits actifs (public)
 */
export const getAllProducts = async (req, res) => {
  try {
    const products = await prisma.product.findMany({
      where: { isActive: true },
      orderBy: { id: "desc" },
      include: {
        supplier: {
          select: {
            companyName: true,
          },
        },
      },
    });

    res.json(products);
  } catch (error) {
    console.error("GET ALL PRODUCTS ERROR:", error);
    res.status(500).json({ message: "Erreur serveur" });
  }
};

