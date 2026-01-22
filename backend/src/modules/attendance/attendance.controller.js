import Attendance from "./attendance.model.js";

// helper to get YYYY-MM-DD
const getToday = () => new Date().toISOString().split("T")[0];

// ✅ Member check-in
export const checkIn = async (req, res) => {
  try {
    const userId = req.user.id;
    const today = getToday();

    const alreadyCheckedIn = await Attendance.findOne({
      user: userId,
      date: today,
    });

    if (alreadyCheckedIn) {
      return res.status(400).json({
        success: false,
        message: "Already checked in today",
      });
    }

    const attendance = await Attendance.create({
      user: userId,
      date: today,
      checkIn: new Date(),
    });

    res.status(201).json({
      success: true,
      attendance,
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

// ✅ Member check-out
export const checkOut = async (req, res) => {
  try {
    const userId = req.user.id;
    const today = getToday();

    const attendance = await Attendance.findOne({
      user: userId,
      date: today,
    });

    if (!attendance) {
      return res.status(400).json({
        success: false,
        message: "No check-in found for today",
      });
    }

    if (attendance.checkOut) {
      return res.status(400).json({
        success: false,
        message: "Already checked out",
      });
    }

    attendance.checkOut = new Date();
    await attendance.save();

    res.json({
      success: true,
      attendance,
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

// ✅ Member attendance history
export const myAttendance = async (req, res) => {
  try {
    const records = await Attendance.find({ user: req.user.id }).sort({
      date: -1,
    });

    res.json({ success: true, records });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

// ✅ Admin / Trainer view
export const getAttendanceByDate = async (req, res) => {
  try {
    const date = req.query.date || getToday();

    const records = await Attendance.find({ date })
      .populate("user", "name role")
      .sort({ checkIn: 1 });

    res.json({ success: true, records });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};
