chrome.webRequest.onCompleted.addListener(
    function(details) {
        let finalUrl = details.url;

        if (finalUrl.includes("code=")) {
            fetch("http://localhost:5000/callback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: finalUrl })
            })
            .catch(error => console.error("Error sending URL:", error));
        }
    },
    { urls: ["https://bharatainternasional.com/?auth_code=*"] }
);
