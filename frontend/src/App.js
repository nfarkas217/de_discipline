import React, { useState, useCallback, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

const categories = [
  "All Students",
  "Black",
  "White",
  "Asian",
  "Hispanic",
  "Students with Disabilities",
  "Low-income students",
];

const TAB_VISUALIZER = "visualizer";
const TAB_OUTLIERS = "outliers";

export default function App() {
  const districts = ["Christina", "Colonial", "Indian River", "Red Clay"];
  const [activeTab, setActiveTab] = useState(TAB_VISUALIZER);
  const [district, setDistrict] = useState("Christina");
  const [outliersDistrict, setOutliersDistrict] = useState("Christina");
  const [outliersData, setOutliersData] = useState([]);
  const [outliersLoading, setOutliersLoading] = useState(false);
  const [outliersError, setOutliersError] = useState("");
  const disciplineOptions = [
    { value: "in_school", label: "In-School Suspension" },
    { value: "out_of_school", label: "Out-of-School Suspension" },
    { value: "both", label: "Both (average)" },
  ];
  const [discipline, setDiscipline] = useState("in_school");
  const [selectedCategories, setSelectedCategories] = useState(categories);
  const [allData, setAllData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const colors = {
    "All Students": "#8b5cf6",
    Black: "#4f46e5",
    White: "#0ea5e9",
    Asian: "#ec4899",
    Hispanic: "#10b981",
    "Students with Disabilities": "#f59e0b",
    "Low-income students": "#ef4444",
  };

  const fetchData = useCallback(
    async (category) => {
      try {
        const response = await fetch(
          `/api/data?category=${encodeURIComponent(category)}&district=${encodeURIComponent(district)}&discipline=${encodeURIComponent(discipline)}`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }

        const result = await response.json();
        return result;
      } catch (err) {
        throw err;
      }
    },
    [district, discipline],
  );

  // Load all data when district or discipline changes
  useEffect(() => {
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
  }, [district, fetchData]);

  // Load outliers when on Outliers tab and district changes
  useEffect(() => {
    if (activeTab !== TAB_OUTLIERS) return;
    const loadOutliers = async () => {
      setOutliersLoading(true);
      setOutliersError("");
      try {
        const res = await fetch(`/api/outliers?district=${encodeURIComponent(outliersDistrict)}`);
        if (!res.ok) throw new Error("Failed to fetch outliers");
        const data = await res.json();
        setOutliersData(data);
      } catch (err) {
        setOutliersError(err.message);
        setOutliersData([]);
      } finally {
        setOutliersLoading(false);
      }
    };
    loadOutliers();
  }, [activeTab, outliersDistrict]);

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

  // Build time-series chart data: one object per year with a key per selected category (PctEnrollment)
  const getChartData = () => {
    if (selectedCategories.length === 0) return [];

    const yearsSet = new Set();
    selectedCategories.forEach((category) => {
      const categoryData = allData[category];
      if (categoryData && categoryData.length > 0) {
        categoryData.forEach((item) => yearsSet.add(item["School Year"]));
      }
    });
    const years = Array.from(yearsSet).sort();

    return years.map((year) => {
      const point = { year };
      selectedCategories.forEach((category) => {
        const categoryData = allData[category];
        const row = categoryData?.find((r) => r["School Year"] === year);
        const isRedacted = row?.redacted === true;
        point[category] =
          row == null ? undefined : isRedacted ? null : Number(row.value);
        point[`${category}_redacted`] = isRedacted;
        point[`${category}_Students`] = row?.Students;
        point[`${category}_Enrollment`] = row?.Enrollment;
      });
      return point;
    });
  };

  // Custom tooltip: show year and each category's value (and optional Students/Enrollment)
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length || !label) return null;
    const data = payload[0]?.payload;
    if (!data) return null;
    return (
      <div
        style={{
          backgroundColor: "white",
          border: "1px solid #ccc",
          padding: "10px",
          borderRadius: "4px",
          minWidth: "160px",
        }}
      >
        <p style={{ margin: 0, fontWeight: "bold", marginBottom: "6px" }}>
          {label}
        </p>
        {selectedCategories.map((cat) => (
          <p key={cat} style={{ margin: "2px 0", fontSize: "0.875rem" }}>
            {cat}:{" "}
            {data[`${cat}_redacted`]
              ? "Redacted"
              : data[cat] != null
                ? Number(data[cat]).toFixed(2) + "%"
                : "—"}
          </p>
        ))}
      </div>
    );
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
        <nav className="tab-nav" aria-label="Main">
          <button
            type="button"
            className={`tab-button ${activeTab === TAB_VISUALIZER ? "tab-button-active" : ""}`}
            onClick={() => setActiveTab(TAB_VISUALIZER)}
          >
            Student Data Filter & Visualizer
          </button>
          <button
            type="button"
            className={`tab-button ${activeTab === TAB_OUTLIERS ? "tab-button-active" : ""}`}
            onClick={() => setActiveTab(TAB_OUTLIERS)}
          >
            Outliers and Deep Dives
          </button>
        </nav>

        {activeTab === TAB_VISUALIZER && (
          <>
            <h1 className="main-title">Student Data Filter & Visualizer</h1>

            <div className="card district-selector">
          <label htmlFor="district-select" className="section-title">
            School District
          </label>
          <select
            id="district-select"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="district-dropdown"
          >
            {districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="card">
          <h2 className="section-title">SubGroup</h2>

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

        <div className="card">
          <h2 className="section-title">Discipline Category</h2>
          <div className="discipline-options">
            {disciplineOptions.map((opt) => (
              <label key={opt.value} className="discipline-option">
                <input
                  type="radio"
                  name="discipline"
                  value={opt.value}
                  checked={discipline === opt.value}
                  onChange={(e) => setDiscipline(e.target.value)}
                  className="discipline-radio"
                />
                <span className="discipline-label">{opt.label}</span>
              </label>
            ))}
          </div>
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
                <LineChart
                  data={getChartData()}
                  margin={{ top: 5, right: 20, left: 80, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="year"
                    label={{
                      value: "School Year",
                      position: "insideBottom",
                      offset: -5,
                    }}
                  />
                  <YAxis
                    label={{
                      value: "Pct of SubGroup Enrollment Disciplined",
                      angle: -90,
                      position: "insideLeft",
                      style: { textAnchor: "middle" },
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  {selectedCategories.map((category) => (
                    <Line
                      key={category}
                      type="monotone"
                      dataKey={category}
                      name={category}
                      stroke={colors[category]}
                      strokeWidth={2}
                      connectNulls={false}
                      dot={(props) => {
                        const { cx, cy, payload, dataKey } = props;
                        const isRedacted = payload[`${dataKey}_redacted`];
                        if (isRedacted) {
                          return (
                            <text
                              x={cx}
                              y={cy}
                              dy={4}
                              textAnchor="middle"
                              fill="#94a3b8"
                              fontSize={9}
                              fontWeight="bold"
                            >
                              R
                            </text>
                          );
                        }
                        return (
                          <circle
                            cx={cx}
                            cy={cy}
                            r={4}
                            fill={colors[category]}
                            stroke="white"
                            strokeWidth={1}
                          />
                        );
                      }}
                    />
                  ))}
                </LineChart>
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
          </>
        )}

        {activeTab === TAB_OUTLIERS && (
          <>
            <h1 className="main-title">Outliers and Deep Dives</h1>
            <div className="card district-selector">
              <label htmlFor="outliers-district-select" className="section-title">
                School District
              </label>
              <select
                id="outliers-district-select"
                value={outliersDistrict}
                onChange={(e) => setOutliersDistrict(e.target.value)}
                className="district-dropdown"
              >
                {districts.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            {outliersLoading && (
              <div className="card loading-container">
                <div className="spinner"></div>
                <p>Loading data...</p>
              </div>
            )}
            {outliersError && (
              <div className="error-box">
                <p><strong>Error:</strong> {outliersError}</p>
              </div>
            )}
            {!outliersLoading && !outliersError && outliersData.length > 0 && (
              <div className="card">
                <h2 className="section-title">
                  Schools by gap (Black % − All Students %), largest gap first
                </h2>
                <p className="outliers-hint">
                  School year: {outliersData[0]?.school_year ?? "—"}
                </p>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>School (Organization)</th>
                        <th>Black %</th>
                        <th>All Students %</th>
                        <th>Difference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outliersData.map((row, idx) => (
                        <tr key={idx}>
                          <td><strong>{row.Organization}</strong></td>
                          <td>{row.black_pct_enrollment != null ? Number(row.black_pct_enrollment).toFixed(2) : "—"}</td>
                          <td>{row.all_students_pct_enrollment != null ? Number(row.all_students_pct_enrollment).toFixed(2) : "—"}</td>
                          <td>{row.difference != null ? Number(row.difference).toFixed(2) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {!outliersLoading && !outliersError && outliersData.length === 0 && (
              <div className="card">
                <p style={{ textAlign: "center", color: "#6b7280" }}>
                  No school-level data for this district.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
