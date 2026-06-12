import React, { useEffect, useState } from "react";
import API from "../api/labApi";
import { useNavigate } from "react-router-dom";

export default function MyReports() {
  const [reports, setReports] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchReports = async () => {
      const token = sessionStorage.getItem("lab2life_token");

      if (!token) {
        navigate("/login", { state: { from: "/my-reports" } });
        return;
      }

      try {
        const response = await API.get("/my-reports", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setReports(response.data.reports || []);
      } catch (error) {
        console.error("Error fetching reports:", error);
      }
    };

    fetchReports();
  }, [navigate]);

  return (
    <div className="pt-32 px-4 md:px-10 pb-16">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">
          My Reports
        </h1>

        {reports.length === 0 ? (
          <p className="text-center text-gray-400">
            No reports found. Upload a report to get started.
          </p>
        ) : (
          <div className="space-y-6">
            {reports.map((report, index) => (
              <div
                key={index}
                className="bg-[#1c1f27] border border-gray-800 rounded-2xl p-6 shadow-lg hover:border-orange-400 transition"
              >
                <h2 className="text-xl font-semibold text-orange-400 mb-2">
                  {report.file_name}
                </h2>

                <p className="text-gray-300">
                  Health Score:{" "}
                  <span className="font-semibold">
                    {report.health_score}/100
                  </span>
                </p>

                <p className="text-gray-300 mb-4">
                  Risk Level:
                    {report.verification_status === "Verified" ? (
                      <div className="mt-3 mb-3">
                        <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm">
                          ✅ Verified by Dr. {report.verified_by_doctor}
                        </span>
                      </div>
                    ) : (
                      <div className="mt-3 mb-3">
                        <span className="bg-yellow-500 text-black px-3 py-1 rounded-full text-sm">
                          Pending Doctor Verification
                        </span>
                      </div>
                  )}
  
                  <span className="font-semibold">
                    {report.risk_level}
                  </span>
                </p>

                <button
                  onClick={() =>
                    navigate("/summary", {
                      state: report,
                    })
                  }
                  className="bg-orange-500 px-4 py-2 rounded-lg hover:bg-orange-600 transition"
                >
                  View Report
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}