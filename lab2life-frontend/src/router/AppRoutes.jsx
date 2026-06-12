import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";

import Home from "../pages/Home";
import UploadReport from "../pages/UploadReport";
import ReportSummary from "../pages/ReportSummary";
import AskDoctor from "../pages/AskDoctor";
import Doctors from "../pages/Doctors";
import NotFound from "../pages/NotFound";
import Login from "../pages/Login";
import Register from "../pages/Register";
import DoctorList from "../pages/DoctorList";
import Subscription from "../pages/Subscription";
import MyReports from "../pages/MyReports";
import DoctorLogin from "../pages/DoctorLogin";
import DoctorDashboard from "../pages/DoctorDashboard";
import DoctorRegister from "../pages/DoctorRegister";

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[#0f1115] text-white">
      <Navbar />
      {children}
      <Footer />
    </div>
  );
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Layout>
              <Home />
            </Layout>
          }
        />

        <Route
          path="/upload"
          element={
            <Layout>
              <UploadReport />
            </Layout>
          }
        />

        <Route
          path="/summary"
          element={
            <Layout>
              <ReportSummary />
            </Layout>
          }
        />
        <Route path="/doctor-login" element={<DoctorLogin />} />
        <Route
          path="/ask-doctor"
          element={
            <Layout>
              <AskDoctor />
            </Layout>
          }
        />
        <Route path="/doctor-dashboard" element={<DoctorDashboard />} />
        <Route
          path="/doctors"
          element={
            <Layout>
              <Doctors />
            </Layout>
          }
        />
        <Route path="/doctor-register" element={<DoctorRegister />} />
        <Route
          path="/doctors/:type"
          element={
            <Layout>
              <DoctorList />
            </Layout>
          }
        />

        <Route
          path="/subscription"
          element={
            <Layout>
              <Subscription />
            </Layout>
          }
        />

        <Route
          path="/login"
          element={
            <Layout>
              <Login />
            </Layout>
          }
        />

        <Route
          path="/register"
          element={
            <Layout>
              <Register />
            </Layout>
          }
        />
        <Route
            path="/my-reports"
            element={
              <Layout>
                <MyReports />
              </Layout>
            }
          />
        <Route
          path="*"
          element={
            <Layout>
              <NotFound />
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}