import mongoose from "mongoose";
import dotenv from "dotenv";
import User from "../modules/users/user.model.js";

dotenv.config();

const seedUsers = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI);

    await User.deleteMany();

    const users = await User.create([
      {
        name: "Gym Admin",
        email: "admin@gym.com",
        password: "123456",
        role: "admin",
      },
      {
        name: "Trainer John",
        email: "trainer@gym.com",
        password: "123456",
        role: "trainer",
      },
      {
        name: "Member Alex",
        email: "member@gym.com",
        password: "123456",
        role: "member",
      },
    ]);

    console.log("Users seeded:", users.map(u => u.email));
    process.exit();
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
};

seedUsers();
