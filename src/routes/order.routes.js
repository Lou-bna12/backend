import express from "express";
import authenticate from "../middlewares/auth.middleware.js";
import { createOrder } from "../controllers/order.controller.js";

const router = express.Router();

router.post("/", authenticate, createOrder);

export default router;
