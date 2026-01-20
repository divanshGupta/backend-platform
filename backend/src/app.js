import express from "express";
import cors from "cors";
import authRoutes from "./modules/auth/auth.routes.js";
import { protect, authorize } from "./middlewares/auth.middleware.js";

const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/auth", authRoutes);

app.get("/api/test/protected", protect, (req, res) => {
  res.json({
    message: "You are authenticated",
    user: req.user,
  });
});

app.get(
  "/api/test/admin",
  protect,
  authorize("admin"),
  (req, res) => {
    res.json({ message: "Welcome Admin" });
  }
);


export default app;