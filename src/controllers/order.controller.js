

import prisma from "../prisma.js";

export const createOrder = async (req, res) => {
  const clientId = req.user.userId;
  const { supplierId, items } = req.body;

  if (!supplierId || !items || items.length === 0) {
    return res.status(400).json({ message: "Commande invalide" });
  }

  try {
    const result = await prisma.$transaction(async (tx) => {
      // 1️⃣ Vérifier le fournisseur
      const supplier = await tx.supplier.findUnique({
        where: { id: supplierId },
      });

      if (!supplier || supplier.status !== "APPROVED") {
        throw new Error("Fournisseur non valide");
      }

      let orderItems = [];
      let totalAmount = 0;

      // 2️⃣ Vérifier produits + stock
      for (const item of items) {
        const product = await tx.product.findUnique({
          where: { id: item.productId },
        });

        if (!product || !product.isActive) {
          throw new Error(`Produit ${item.productId} indisponible`);
        }

        if (product.stock < item.quantity) {
          throw new Error(
            `Stock insuffisant pour le produit ${product.name}`
          );
        }

        // décrément stock
        await tx.product.update({
          where: { id: product.id },
          data: {
            stock: { decrement: item.quantity },
          },
        });

        orderItems.push({
          productId: product.id,
          quantity: item.quantity,
          price: product.price,
        });

        totalAmount += product.price * item.quantity;
      }

      // 3️⃣ Créer la commande
      const order = await tx.order.create({
        data: {
          clientId,
          supplierId,
          status: "CREATED",
          items: {
            create: orderItems,
          },
        },
        include: {
          items: true,
        },
      });

      return { order, totalAmount };
    });

    res.status(201).json({
      message: "Commande créée avec succès",
      order: result.order,
      totalAmount: result.totalAmount,
    });
  } catch (error) {
    console.error(error.message);
    res.status(400).json({ message: error.message });
  }
};


export const getMyOrders = async (req, res) => {
  const clientId = req.user.userId;

  const orders = await prisma.order.findMany({
    where: { clientId },
    include: {
      items: {
        include: { product: true },
      },
      supplier: true,
    },
  });

  res.json(orders);
};
