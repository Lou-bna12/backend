import express from "express";
import authenticate from "../middlewares/auth.middleware.js";
import {
  getMySupplierProfile,
  updateOrderStatus,
} from "../controllers/supplier.controller.js";

const router = express.Router();

router.get("/me", authenticate, getMySupplierProfile);
router.put("/orders/:id/status", authenticate, updateOrderStatus);

export default router;
