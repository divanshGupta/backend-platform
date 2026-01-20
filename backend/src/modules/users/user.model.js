import mongoose from "mongoose";
import bcrypt from "bcrypt";

const userSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },

    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
    },

    password: {
      type: String,
      required: true,
      select: false, // 🔐 critical for security
    },

    role: {
      type: String,
      enum: ["admin", "trainer", "member"],
      default: "member",
    },

    phone: String,

    trainer: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User", // trainer is also a user
    },

    height: Number,
    weight: Number,
    goal: {
      type: String,
      enum: ["fat_loss", "muscle_gain", "maintenance"],
    },

    isActive: {
      type: Boolean,
      default: true,
    },
  },
  { timestamps: true }
);

// Hash password before save
userSchema.pre("save", async function () {
  if (!this.isModified("password")) return;
  this.password = await bcrypt.hash(this.password, 10);
});


// Compare password
userSchema.methods.comparePassword = function (candidatePassword) {
  return bcrypt.compare(candidatePassword, this.password);
};

export default mongoose.model("User", userSchema);
