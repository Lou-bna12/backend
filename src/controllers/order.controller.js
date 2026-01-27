import prisma from "../prisma.js";

// ==========================
// CREATE ORDER (CLIENT)
// ==========================
export const createOrder = async (req, res) => {
  const clientId = req.user.id;
  const { items } = req.body;

  if (!items || items.length === 0) {
    return res.status(400).json({ message: "Commande vide" });
  }

  try {
    const result = await prisma.$transaction(async (tx) => {
      // 1️⃣ Créer la commande globale
      const order = await tx.order.create({
        data: {
          clientId,
          status: "CREATED",
        },
      });

      let totalAmount = 0;

      // 2️⃣ Créer les OrderItems
      for (const item of items) {
        const product = await tx.product.findUnique({
          where: { id: item.productId },
        });

        if (!product || !product.isActive) {
          throw new Error("Produit indisponible");
        }

        if (product.stock < item.quantity) {
          throw new Error(`Stock insuffisant pour ${product.name}`);
        }

        // décrément stock
        await tx.product.update({
          where: { id: product.id },
          data: {
            stock: { decrement: item.quantity },
          },
        });

        await tx.orderItem.create({
          data: {
            orderId: order.id,
            productId: product.id,
            supplierId: product.supplierId,
            quantity: item.quantity,
            price: product.price,
            status: "CREATED",
          },
        });

        totalAmount += product.price * item.quantity;
      }

      return {
        orderId: order.id,
        totalAmount,
      };
    });

    res.status(201).json({
      message: "Commande créée avec succès",
      orderId: result.orderId,
      totalAmount: result.totalAmount,
    });
  } catch (error) {
    console.error("CREATE ORDER ERROR:", error.message);
    res.status(400).json({ message: error.message });
  }
};
