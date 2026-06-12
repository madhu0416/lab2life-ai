import React, { useState } from "react";
import API from "../api/labApi";
import { useNavigate } from "react-router-dom";

export default function DoctorRegister() {

  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    specialization: "",
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();

    try {

      await API.post(
        "/doctor-register",
        formData
      );

      alert("Doctor registered successfully");

      navigate("/doctor-login");

    } catch (error) {

      console.error(error);

      alert(
        error.response?.data?.detail ||
        "Registration failed"
      );
    }
  };

  return (
    <div className="min-h-screen flex justify-center items-center bg-[#0f1117] px-4">

      <div className="bg-[#1c1f27] p-8 rounded-2xl w-full max-w-md shadow-lg">

        <h1 className="text-3xl font-bold text-center text-orange-400 mb-6">
          Doctor Registration
        </h1>

        <form
          onSubmit={handleRegister}
          className="space-y-5"
        >

          <input
            type="text"
            name="full_name"
            placeholder="Full Name"
            value={formData.full_name}
            onChange={handleChange}
            required
            className="w-full p-3 rounded-lg bg-[#111827] border border-gray-700 text-white"
          />

          <input
            type="email"
            name="email"
            placeholder="Email"
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

          <input
            type="text"
            name="specialization"
            placeholder="Specialization"
            value={formData.specialization}
            onChange={handleChange}
            required
            className="w-full p-3 rounded-lg bg-[#111827] border border-gray-700 text-white"
          />

          <button
            type="submit"
            className="w-full bg-orange-500 hover:bg-orange-600 transition py-3 rounded-lg font-semibold"
          >
            Register
          </button>

        </form>

      </div>
    </div>
  );
}