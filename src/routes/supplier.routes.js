import express from "express";
import { createSupplierProfile } from "../controllers/supplier.controller.js";
import authenticate from "../middlewares/auth.middleware.js";
import { authorize } from "../middlewares/role.middleware.js";


const router = express.Router();

/**
 * Création du profil fournisseur
 * POST /api/suppliers/profile
 */
router.post(
  "/profile",
  authenticate,
  authorize("SUPPLIER"),
  createSupplierProfile
);

export default router;
