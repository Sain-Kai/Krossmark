const BASE_URL = "http://10.0.2.2:8000/api/v1";

export const getLatestResult = async () => {
  try {
    const res = await fetch(`${BASE_URL}/results/latest/`);

    if (res.status === 404) return { status: "no_data" };

    const json = await res.json();
    return json;
  } catch (err) {
    console.log("API ERROR:", err);
    return { status: "error" };
  }
};