import express from "express";
import authenticate from "../middlewares/auth.middleware.js";

import {
  createOrder,
  getMyOrders,
} from "../controllers/order.controller.js";

const router = express.Router();

router.post("/", authenticate, createOrder);
router.get("/me", authenticate, getMyOrders);

export default router;
