const userSearchInput = document.getElementById("userSearchInput");
const userSearchResults = document.getElementById("userSearchResults");

let userSearchTimer = null;

function renderUserSearchResults(users) {
  if (!userSearchResults) return;

  if (!users.length) {
    userSearchResults.innerHTML = '<p class="search-empty">No commanders found.</p>';
    return;
  }

  userSearchResults.innerHTML = users.map((user) => `
    <a class="user-result" href="${user.profile_url}">
      <span>
        <strong>${user.username}</strong>
        <em>${user.colony_name || "Private colony"}</em>
      </span>
      <small>${user.is_public ? "Public colony" : "Private profile"}</small>
    </a>
  `).join("");
}

async function searchUsers(query) {
  if (!userSearchResults) return;

  if (query.length < 2) {
    userSearchResults.innerHTML = '<p class="search-empty">Type at least 2 letters to search commanders.</p>';
    return;
  }

  userSearchResults.innerHTML = '<p class="search-empty">Searching...</p>';

  try {
    const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error("Search failed.");
    const users = await response.json();
    renderUserSearchResults(users);
  } catch (error) {
    userSearchResults.innerHTML = '<p class="search-empty">Search is unavailable right now.</p>';
  }
}

if (userSearchInput) {
  userSearchResults.innerHTML = '<p class="search-empty">Type at least 2 letters to search commanders.</p>';
  userSearchInput.addEventListener("input", (event) => {
    clearTimeout(userSearchTimer);
    userSearchTimer = setTimeout(() => {
      searchUsers(event.target.value.trim());
    }, 250);
  });
}
