async function setPreferences(
  preferred_price,
  max_distance,
  preferred_cuisine,
  dietary_restrictions,
  other = undefined
) {
  const prefs = {
    preferred_price,
    max_distance,
    preferred_cuisine,
    dietary_restrictions,
    other,
  };
    await fetch("/preferences", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        },
        body: JSON.stringify(prefs),
    });
}

async function getPreferences() {
    const response = await fetch("/preferences", {
        method: "GET",
        headers: {
        "Content-Type": "application/json",
        },
    })
    return await response.json();
}
