import React, { useEffect, useState } from "react";
import API from "../api/labApi";

export default function DoctorDashboard() {
  const [reports, setReports] = useState([]);
  const [editedSummary, setEditedSummary] = useState({});

  const fetchReports = async () => {
    try {
      const token = sessionStorage.getItem("doctor_token");

      const response = await API.get("/doctor/pending-reports", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setReports(response.data.reports || []);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const verifyReport = async (reportId) => {
    try {
      const token = sessionStorage.getItem("doctor_token");

      await API.put(
        `/doctor/verify-report/${reportId}`,
        {
          corrected_summary:
            editedSummary[reportId] ||
            reports.find((r) => r.report_id === reportId)?.summary,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      alert("Report verified successfully");

      fetchReports();
    } catch (error) {
      console.error(error);
      alert("Verification failed");
    }
  };

  return (
    <div className="min-h-screen bg-[#0f1117] text-white p-6">
      <h1 className="text-4xl font-bold mb-8 text-center text-orange-400">
        Doctor Dashboard
      </h1>

      {reports.length === 0 ? (
        <p className="text-center text-gray-400">
          No pending reports found
        </p>
      ) : (
        <div className="space-y-8">
          {reports.map((report) => (
            <div
              key={report.report_id}
              className="bg-[#1c1f27] p-6 rounded-2xl border border-gray-700"
            >
              <h2 className="text-2xl font-semibold text-orange-300 mb-2">
                {report.file_name}
              </h2>

              <p className="mb-2">
                <span className="font-semibold">Patient:</span>{" "}
                {report.patient_name}
              </p>

              <p className="mb-4">
                <span className="font-semibold">Status:</span>{" "}
                {report.verification_status}
              </p>

              <textarea
                className="w-full h-56 bg-[#111827] border border-gray-600 rounded-xl p-4 text-sm"
                defaultValue={report.summary}
                onChange={(e) =>
                  setEditedSummary({
                    ...editedSummary,
                    [report.report_id]: e.target.value,
                  })
                }
              />

              <button
                onClick={() => verifyReport(report.report_id)}
                className="mt-4 bg-green-600 hover:bg-green-700 px-6 py-2 rounded-xl font-semibold"
              >
                Verify Report
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}