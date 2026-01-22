import express from "express";
import { authorize, protect } from "../../middlewares/auth.middleware.js";
import User from "./user.model.js";

const router = express.Router();

router.get("/me", protect, async (req, res) => {
  const user = await User.findById(req.user.id);
  res.json(user);
});

router.get(
  "/",
  protect,
  authorize("admin"),
  async (req, res) => {
    const users = await User.find();
    res.json(users);
  }
);


export default router;
