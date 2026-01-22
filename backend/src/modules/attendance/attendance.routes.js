import express from "express";
import {
  checkIn,
  checkOut,
  myAttendance,
  getAttendanceByDate,
} from "./attendance.controller.js";

import { protect, authorize } from "../../middlewares/auth.middleware.js";

const router = express.Router();

// member
router.post("/check-in", protect, authorize("member"), checkIn);
router.post("/check-out", protect, authorize("member"), checkOut);
router.get("/me", protect, authorize("member"), myAttendance);

// admin / trainer
router.get(
  "/",
  protect,
  authorize("admin", "trainer"),
  getAttendanceByDate
);

export default router;
