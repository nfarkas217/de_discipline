import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

export default function App() {
  const categories = [
    "All Students",
    "Black",
    "Hispanic",
    "Students with Disabilities",
    "Low-income students",
  ];

  const [selectedCategories, setSelectedCategories] = useState(categories);
  const [allData, setAllData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const colors = {
    "All Students": "#8b5cf6",
    Black: "#4f46e5",
    Hispanic: "#10b981",
    "Students with Disabilities": "#f59e0b",
    "Low-income students": "#ef4444",
  };

  // Load all data on component mount
  React.useEffect(() => {
    const loadAllData = async () => {
      setLoading(true);
      setError("");
      const dataPromises = categories.map((category) => fetchData(category));

      try {
        const results = await Promise.all(dataPromises);
        const newData = {};
        categories.forEach((category, index) => {
          newData[category] = results[index];
        });
        setAllData(newData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadAllData();
  }, []);

  const fetchData = async (category) => {
    try {
      const response = await fetch(
        `/api/data?category=${encodeURIComponent(category)}`,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch data");
      }

      const result = await response.json();
      return result;
    } catch (err) {
      throw err;
    }
  };

  const handleCategoryToggle = async (category) => {
    const isCurrentlySelected = selectedCategories.includes(category);

    if (isCurrentlySelected) {
      // Remove category
      setSelectedCategories(selectedCategories.filter((c) => c !== category));
      const newData = { ...allData };
      delete newData[category];
      setAllData(newData);
    } else {
      // Add category
      setLoading(true);
      setError("");

      try {
        const data = await fetchData(category);
        setSelectedCategories([...selectedCategories, category]);
        setAllData({ ...allData, [category]: data });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
  };

  // Prepare data for the chart by combining all selected categories
  const getChartData = () => {
    if (selectedCategories.length === 0) return [];

    const chartData = [];

    // Get all unique names (in this case, just the category itself)
    selectedCategories.forEach((category) => {
      const categoryData = allData[category];
      if (categoryData && categoryData.length > 0) {
        categoryData.forEach((item) => {
          chartData.push({
            name: category,
            PctEnrollment: item.value,
            Students: item.Students,
            Enrollment: item.Enrollment,
            category: category,
            fill: colors[category],
          });
        });
      }
    });

    return chartData;
  };

  // Custom tooltip to show Students / Enrollment
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: "white",
            border: "1px solid #ccc",
            padding: "10px",
            borderRadius: "4px",
          }}
        >
          <p style={{ margin: 0, fontWeight: "bold" }}>{data.name}</p>
          <p style={{ margin: "5px 0 0 0" }}>
            {data.Students} / {data.Enrollment}
          </p>
        </div>
      );
    }
    return null;
  };

  // Get all table data
  const getAllTableData = () => {
    const tableData = [];
    selectedCategories.forEach((category) => {
      const categoryData = allData[category];
      if (categoryData) {
        categoryData.forEach((item) => {
          tableData.push({ ...item, Category: category });
        });
      }
    });
    return tableData;
  };

  return (
    <div className="app-container">
      <div className="content-wrapper">
        <h1 className="main-title">Student Data Filter & Visualizer</h1>

        <div className="card">
          <h2 className="section-title">
            Select Categories (Multiple Selection)
          </h2>

          <div className="category-grid">
            {categories.map((category) => (
              <label key={category} className="checkbox-container">
                <input
                  type="checkbox"
                  checked={selectedCategories.includes(category)}
                  onChange={() => handleCategoryToggle(category)}
                  className="checkbox-input"
                />
                <span className="checkbox-label">{category}</span>
              </label>
            ))}
          </div>

          {selectedCategories.length > 0 && (
            <button
              onClick={() => {
                setSelectedCategories([]);
                setAllData({});
              }}
              className="clear-button"
            >
              Clear All Selections
            </button>
          )}
        </div>

        {loading && (
          <div className="card loading-container">
            <div className="spinner"></div>
            <p>Loading data...</p>
          </div>
        )}

        {error && (
          <div className="error-box">
            <p>
              <strong>Error:</strong> {error}
            </p>
            <p className="error-hint">
              Make sure your FastAPI backend is running and the proxy is
              configured in package.json
            </p>
          </div>
        )}

        {!loading && selectedCategories.length > 0 && (
          <div className="card">
            <h2 className="section-title">
              Comparison: {selectedCategories.join(", ")}
            </h2>

            <div className="chart-container">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={getChartData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    label={{
                      value: "Subgroup",
                      position: "insideBottom",
                      offset: -5,
                    }}
                  />
                  <YAxis
                    label={{
                      value: "PctEnrollment",
                      angle: -90,
                      position: "insideLeft",
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="PctEnrollment" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {getAllTableData().length > 0 && (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      {Object.keys(getAllTableData()[0] || {})
                        .filter(
                          (key) =>
                            key !== "Category" &&
                            key !== "index" &&
                            key !== "name",
                        )
                        .map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {getAllTableData().map((row, idx) => (
                      <tr key={idx}>
                        <td>
                          <strong>{row.Category}</strong>
                        </td>
                        {Object.entries(row)
                          .filter(
                            ([key]) =>
                              key !== "Category" &&
                              key !== "index" &&
                              key !== "name",
                          )
                          .map(([key, value], i) => (
                            <td key={i}>{value}</td>
                          ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {!loading && selectedCategories.length === 0 && (
          <div className="card">
            <p style={{ textAlign: "center", color: "#6b7280" }}>
              Select one or more categories above to view data
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
