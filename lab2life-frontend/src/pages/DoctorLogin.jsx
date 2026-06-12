import React, { useState } from "react";
import API from "../api/labApi";
import { useNavigate } from "react-router-dom";

export default function DoctorLogin() {

  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    try {

      const response = await API.post(
        "/doctor-login",
        formData
      );

      // ✅ SAVE TOKEN
      sessionStorage.setItem(
        "doctor_token",
        response.data.access_token
      );

      sessionStorage.setItem(
        "doctor_name",
        response.data.doctor_name
      );

      alert("Doctor login successful");

      // ✅ REDIRECT
      navigate("/doctor-dashboard");

    } catch (error) {

      console.error(error);

      alert(
        error.response?.data?.detail ||
        "Login failed"
      );
    }
  };

  return (
    <div className="min-h-screen flex justify-center items-center bg-[#0f1117]">

      <div className="bg-[#1c1f27] p-8 rounded-2xl w-full max-w-md shadow-lg">

        <h1 className="text-3xl font-bold text-center text-orange-400 mb-6">
          Doctor Login
        </h1>

        <form onSubmit={handleLogin} className="space-y-5">

          <input
            type="email"
            name="email"
            placeholder="Doctor Email"
            value={formData.email}
            onChange={handleChange}
            required
            className="w-full p-3 rounded-lg bg-[#111827] border border-gray-700 text-white"
          />

          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
            required
            className="w-full p-3 rounded-lg bg-[#111827] border border-gray-700 text-white"
          />

          <button
            type="submit"
            className="w-full bg-orange-500 hover:bg-orange-600 transition py-3 rounded-lg font-semibold"
          >
            Login
          </button>

        </form>
      </div>
    </div>
  );
}