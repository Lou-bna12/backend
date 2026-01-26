import express from "express";
import authenticate from "../middlewares/auth.middleware.js";
import { isAdmin } from "../middlewares/admin.middleware.js";
import {
  getPendingSuppliers,
  approveSupplier,
  rejectSupplier,
} from "../controllers/admin.controller.js";

const router = express.Router();

router.get("/suppliers/pending", authenticate, isAdmin, getPendingSuppliers);
router.put("/suppliers/:id/approve", authenticate, isAdmin, approveSupplier);
router.put("/suppliers/:id/reject", authenticate, isAdmin, rejectSupplier);

export default router;
