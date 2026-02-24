import React, { useState, useCallback, useEffect, useMemo } from "react";
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
  const [outliersSortConfig, setOutliersSortConfig] = useState({
    key: "difference",
    direction: "descending",
  });
  const [deepDiveSchool, setDeepDiveSchool] = useState(null);
  const [deepDiveData, setDeepDiveData] = useState([]);
  const [deepDiveLoading, setDeepDiveLoading] = useState(false);
  const [deepDiveError, setDeepDiveError] = useState("");
  const [deepDiveDiscipline, setDeepDiveDiscipline] = useState(
    "In-School Suspension",
  );
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
    "All Students": "#10b981",
    Black: "#3b82f6",
    "African American": "#3b82f6",
    White: "#0ea5e9",
    Asian: "#ec4899",
    Hispanic: "#8b5cf6",
    "Students with Disabilities": "#f59e0b",
    "Low-income students": "#ef4444",
    "Low Income": "#ef4444",
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
        const res = await fetch(
          `/api/outliers?district=${encodeURIComponent(outliersDistrict)}`,
        );
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

  useEffect(() => {
    if (!deepDiveSchool) {
      setDeepDiveData([]); // Clear data when closing deep dive
      return;
    }
    const loadDeepDiveData = async () => {
      setDeepDiveLoading(true);
      setDeepDiveError("");
      try {
        const res = await fetch(
          `/api/school-deep-dive?school=${encodeURIComponent(deepDiveSchool)}`,
        );
        if (!res.ok)
          throw new Error(
            `Failed to fetch deep dive data for ${deepDiveSchool}`,
          );
        const data = await res.json();
        setDeepDiveData(data);
      } catch (err) {
        setDeepDiveError(err.message);
        setDeepDiveData([]);
      } finally {
        setDeepDiveLoading(false);
      }
    };
    loadDeepDiveData();
  }, [deepDiveSchool]);

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

  const { deepDiveChartData, deepDiveSubGroups } = useMemo(() => {
    if (!deepDiveData || deepDiveData.length === 0) {
      return { deepDiveChartData: [], deepDiveSubGroups: [] };
    }

    const deepDiveSubgroupsToShow = [
      "African American",
      "Low Income",
      "Students with Disabilities",
      "All Students",
    ];

    const filteredData = deepDiveData.filter(
      (d) =>
        d.Category === deepDiveDiscipline &&
        deepDiveSubgroupsToShow.includes(d.SubGroup),
    );
    if (filteredData.length === 0) {
      return { deepDiveChartData: [], deepDiveSubGroups: [] };
    }

    const yearsSet = new Set();
    const subGroupsSet = new Set();
    filteredData.forEach((item) => {
      yearsSet.add(item["School Year"]);
      subGroupsSet.add(item.SubGroup);
    });

    const years = Array.from(yearsSet).sort();
    const subGroups = Array.from(subGroupsSet).sort();

    const chartData = years.map((year) => {
      const point = { year };
      subGroups.forEach((subgroup) => {
        const row = filteredData.find(
          (d) => d["School Year"] === year && d.SubGroup === subgroup,
        );
        const isRedacted = row?.Rowstatus?.toUpperCase() === "REDACTED";
        point[subgroup] =
          row == null
            ? undefined
            : isRedacted
              ? null
              : Number(row.PctEnrollment);
        point[`${subgroup}_redacted`] = isRedacted;
      });
      return point;
    });

    return { deepDiveChartData: chartData, deepDiveSubGroups: subGroups };
  }, [deepDiveData, deepDiveDiscipline]);

  const requestOutliersSort = (key) => {
    let direction = "descending";
    if (
      outliersSortConfig.key === key &&
      outliersSortConfig.direction === "descending"
    ) {
      direction = "ascending";
    }
    setOutliersSortConfig({ key, direction });
  };

  const sortedOutliersData = useMemo(() => {
    if (!outliersData || outliersData.length === 0) return [];
    const sortableItems = [...outliersData];
    if (outliersSortConfig.key) {
      sortableItems.sort((a, b) => {
        if (a[outliersSortConfig.key] === null) return 1;
        if (b[outliersSortConfig.key] === null) return -1;
        if (a[outliersSortConfig.key] < b[outliersSortConfig.key]) {
          return outliersSortConfig.direction === "ascending" ? -1 : 1;
        }
        if (a[outliersSortConfig.key] > b[outliersSortConfig.key]) {
          return outliersSortConfig.direction === "ascending" ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [outliersData, outliersSortConfig]);

  // Custom tooltip: show year and each category's value (and optional Students/Enrollment)
  const CustomTooltip = ({ active, payload, label, series }) => {
    if (!active || !payload?.length || !label || !series) return null;
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
        {series.map((cat) => (
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
                      <Tooltip
                        content={<CustomTooltip series={selectedCategories} />}
                      />
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
            {deepDiveSchool ? (
              <div className="card">
                <button
                  onClick={() => setDeepDiveSchool(null)}
                  className="clear-button"
                  style={{ marginBottom: "1rem", float: "left" }}
                >
                  &larr; Back to Outliers List
                </button>
                <h2
                  className="section-title"
                  style={{ marginTop: 0, paddingTop: "40px" }}
                >
                  Deep Dive: {deepDiveSchool}
                </h2>

                {deepDiveLoading && (
                  <div className="card loading-container">
                    <div className="spinner"></div>
                    <p>Loading deep dive...</p>
                  </div>
                )}
                {deepDiveError && (
                  <div className="error-box">
                    <p>
                      <strong>Error:</strong> {deepDiveError}
                    </p>
                  </div>
                )}
                {!deepDiveLoading &&
                  !deepDiveError &&
                  deepDiveData.length > 0 && (
                    <>
                      <div className="card">
                        <h3 className="section-title">Discipline Category</h3>
                        <div className="discipline-options">
                          {[
                            "In-School Suspension",
                            "Out-of-School Suspension",
                          ].map((opt) => (
                            <label key={opt} className="discipline-option">
                              <input
                                type="radio"
                                name="deep-dive-discipline"
                                value={opt}
                                checked={deepDiveDiscipline === opt}
                                onChange={(e) =>
                                  setDeepDiveDiscipline(e.target.value)
                                }
                                className="discipline-radio"
                              />
                              <span className="discipline-label">{opt}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      <div className="chart-container">
                        <h3 className="section-title">
                          Trend over last 3 available years
                        </h3>
                        <ResponsiveContainer width="100%" height={400}>
                          <LineChart
                            data={deepDiveChartData}
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
                            <Tooltip
                              content={
                                <CustomTooltip series={deepDiveSubGroups} />
                              }
                            />
                            <Legend />
                            {deepDiveSubGroups.map((subgroup) => (
                              <Line
                                key={subgroup}
                                type="monotone"
                                dataKey={subgroup}
                                name={subgroup}
                                stroke={colors[subgroup] || "#8884d8"}
                                strokeWidth={2}
                                connectNulls={false}
                              />
                            ))}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="table-container">
                        <h3 className="section-title">
                          Raw Data ({deepDiveDiscipline})
                        </h3>
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>School Year</th>
                              <th>SubGroup</th>
                              <th>Students</th>
                              <th>Enrollment</th>
                              <th>PctEnrollment</th>
                              <th>Incidents</th>
                              <th>Rowstatus</th>
                            </tr>
                          </thead>
                          <tbody>
                            {deepDiveData
                              .filter(
                                (row) =>
                                  row.Category === deepDiveDiscipline &&
                                  [
                                    "African American",
                                    "Low Income",
                                    "Students with Disabilities",
                                    "All Students",
                                  ].includes(row.SubGroup),
                              )
                              .map((row, idx) => (
                                <tr key={idx}>
                                  <td>{row["School Year"]}</td>
                                  <td>{row.SubGroup}</td>
                                  <td>{row.Students}</td>
                                  <td>{row.Enrollment}</td>
                                  <td>
                                    {row.PctEnrollment != null
                                      ? `${Number(row.PctEnrollment).toFixed(
                                          2,
                                        )}`
                                      : "—"}
                                  </td>
                                  <td>{row.Incidents}</td>
                                  <td>{row.Rowstatus}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                {!deepDiveLoading &&
                  !deepDiveError &&
                  deepDiveData.length === 0 && (
                    <p>No data available for this school.</p>
                  )}
              </div>
            ) : (
              <>
                <div className="card district-selector">
                  <label
                    htmlFor="outliers-district-select"
                    className="section-title"
                  >
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
                    <p>
                      <strong>Error:</strong> {outliersError}
                    </p>
                  </div>
                )}
                {!outliersLoading &&
                  !outliersError &&
                  outliersData.length > 0 && (
                    <div className="card">
                      <h2 className="section-title">
                        Schools by In-School suspension gap (Black % − All
                        Students %), largest gap first
                      </h2>
                      <p className="outliers-hint">
                        School year: {outliersData[0]?.school_year ?? "—"}
                      </p>
                      <div className="table-container">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th className="sortable-header-container">
                                <button
                                  type="button"
                                  onClick={() =>
                                    requestOutliersSort("Organization")
                                  }
                                  className="sortable-header"
                                >
                                  School (Organization)
                                  {outliersSortConfig.key ===
                                    "Organization" && (
                                    <span className="sort-arrow">
                                      {outliersSortConfig.direction ===
                                      "descending"
                                        ? " 🔽"
                                        : " 🔼"}
                                    </span>
                                  )}
                                </button>
                              </th>
                              <th className="sortable-header-container">
                                <button
                                  type="button"
                                  onClick={() =>
                                    requestOutliersSort("black_pct_enrollment")
                                  }
                                  className="sortable-header"
                                >
                                  Black (% and count)
                                  {outliersSortConfig.key ===
                                    "black_pct_enrollment" && (
                                    <span className="sort-arrow">
                                      {outliersSortConfig.direction ===
                                      "descending"
                                        ? " 🔽"
                                        : " 🔼"}
                                    </span>
                                  )}
                                </button>
                              </th>
                              <th className="sortable-header-container">
                                <button
                                  type="button"
                                  onClick={() =>
                                    requestOutliersSort(
                                      "all_students_pct_enrollment",
                                    )
                                  }
                                  className="sortable-header"
                                >
                                  All Students (% and count)
                                  {outliersSortConfig.key ===
                                    "all_students_pct_enrollment" && (
                                    <span className="sort-arrow">
                                      {outliersSortConfig.direction ===
                                      "descending"
                                        ? " 🔽"
                                        : " 🔼"}
                                    </span>
                                  )}
                                </button>
                              </th>
                              <th className="sortable-header-container">
                                <button
                                  type="button"
                                  onClick={() =>
                                    requestOutliersSort("difference")
                                  }
                                  className="sortable-header"
                                >
                                  Difference
                                  {outliersSortConfig.key === "difference" && (
                                    <span className="sort-arrow">
                                      {outliersSortConfig.direction ===
                                      "descending"
                                        ? " 🔽"
                                        : " 🔼"}
                                    </span>
                                  )}
                                </button>
                              </th>
                              <th className="sortable-header-container">
                                <button
                                  type="button"
                                  onClick={() =>
                                    requestOutliersSort("incident_rate")
                                  }
                                  className="sortable-header"
                                >
                                  Incident Rate{" "}
                                  <span
                                    title="Total incidents divided by total enrollment. Can be >100% if students receive multiple suspensions."
                                    style={{
                                      cursor: "help",
                                      fontWeight: "normal",
                                    }}
                                  >
                                    &#9432;
                                  </span>
                                  {outliersSortConfig.key ===
                                    "incident_rate" && (
                                    <span className="sort-arrow">
                                      {outliersSortConfig.direction ===
                                      "descending"
                                        ? " 🔽"
                                        : " 🔼"}
                                    </span>
                                  )}
                                </button>
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {sortedOutliersData.map((row, idx) => (
                              <tr key={idx}>
                                <td>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setDeepDiveSchool(row.Organization)
                                    }
                                    style={{
                                      background: "none",
                                      border: "none",
                                      padding: 0,
                                      color: "#4f46e5",
                                      textDecoration: "underline",
                                      cursor: "pointer",
                                      fontWeight: "bold",
                                      fontFamily: "inherit",
                                      fontSize: "inherit",
                                    }}
                                  >
                                    {row.Organization}
                                  </button>
                                </td>
                                <td>
                                  {row.black_pct_enrollment != null ? (
                                    <>
                                      {`${Number(
                                        row.black_pct_enrollment,
                                      ).toFixed(2)}%`}
                                      <span
                                        style={{
                                          fontSize: "0.8em",
                                          color: "#666",
                                          marginLeft: "5px",
                                        }}
                                      >
                                        ({row.black_students} /{" "}
                                        {row.black_enrollment})
                                      </span>
                                    </>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                                <td>
                                  {row.all_students_pct_enrollment != null ? (
                                    <>
                                      {`${Number(
                                        row.all_students_pct_enrollment,
                                      ).toFixed(2)}%`}
                                      <span
                                        style={{
                                          fontSize: "0.8em",
                                          color: "#666",
                                          marginLeft: "5px",
                                        }}
                                      >
                                        ({row.all_students_students} /{" "}
                                        {row.all_students_enrollment})
                                      </span>
                                    </>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                                <td>
                                  {row.difference != null
                                    ? Number(row.difference).toFixed(2)
                                    : "—"}
                                </td>
                                <td>
                                  {row.incident_rate != null
                                    ? `${(row.incident_rate * 100).toFixed(2)}%`
                                    : "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                {!outliersLoading &&
                  !outliersError &&
                  outliersData.length === 0 && (
                    <div className="card">
                      <p style={{ textAlign: "center", color: "#6b7280" }}>
                        No school-level data for this district.
                      </p>
                    </div>
                  )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
