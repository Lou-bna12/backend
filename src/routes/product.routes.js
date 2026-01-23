import express from "express";
import { createProduct, getMyProducts } from "../controllers/product.controller.js";
import authenticate from "../middlewares/auth.middleware.js";

const router = express.Router();

// 🔐 Fournisseur uniquement
router.post("/", authenticate, createProduct);
router.get("/me", authenticate, getMyProducts);

export default router;
