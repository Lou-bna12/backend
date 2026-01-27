import express from "express";
import {
  createProduct,
  getMyProducts,
  getAllProducts,
} from "../controllers/product.controller.js";
import authenticate from "../middlewares/auth.middleware.js";
import { authorize } from "../middlewares/role.middleware.js";

const router = express.Router();

router.post("/", authenticate, authorize("SUPPLIER"), createProduct);
router.get("/me", authenticate, authorize("SUPPLIER"), getMyProducts);

// 🌍 Public
router.get("/", getAllProducts);

export default router;
