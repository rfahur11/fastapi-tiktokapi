const socket = io('http://' + document.domain + ':' + location.port, {path: '/socket.io/'});

function startOAuth() {
    let oauthWindow = window.open('/oauth', '_blank', 'width=500,height=600');
    let timeout = setTimeout(() => oauthWindow?.close(), 300000);
    document.addEventListener("visibilitychange", () => !document.hidden && oauthWindow?.close() && clearTimeout(timeout));
    window.addEventListener("beforeunload", () => oauthWindow?.close());
}

function toggleToken() {
    const tokenSection = document.getElementById('tokenSection');
    const tokenArrow = document.getElementById('tokenArrow');
    tokenSection.classList.toggle('hidden');
    tokenArrow.classList.toggle('fa-chevron-up', !tokenSection.classList.contains('hidden'));
    tokenArrow.classList.toggle('fa-chevron-down', tokenSection.classList.contains('hidden'));
    if (!tokenSection.classList.contains('hidden')) fetchToken();
}

async function fetchToken() {
    try {
    const response = await fetch('/get_latest_token');
    const data = await response.json();
    document.getElementById("tokenDisplay").innerText = data.access_token || "No Token Available";
    } catch {
    document.getElementById("tokenDisplay").innerText = "Failed to load token";
    }
}

function openModal(modalId, contentId, fetchFunction) {
    const modal = document.getElementById(modalId);
    const modalContent = document.getElementById(contentId);
    modal.classList.remove('hidden');
    modalContent.classList.remove('opacity-0', 'modal-close');
    modalContent.classList.add('modal-open');
    fetchFunction();
}

function closeModal(modalId, contentId) {
    const modal = document.getElementById(modalId);
    const modalContent = document.getElementById(contentId);
    modalContent.classList.remove('modal-open');
    modalContent.classList.add('modal-close');
    modalContent.addEventListener('animationend', () => modal.classList.add('hidden'), { once: true });
}

async function fetchData(url, selectId, defaultText, callback) {
    const selectElement = document.getElementById(selectId);
    selectElement.innerHTML = `<option value="">${defaultText}</option>`;
    try {
        const response = await fetch(url);
        const data = await response.json();
        if (!data?.data || !Array.isArray(data.data)) throw new Error("Invalid data format");
        selectElement.innerHTML = data.data.length === 0 ? `<option value="">No data available</option>` : data.data.map((item, index) => `<option value="${item.id}" ${index === 0 ? 'selected' : ''}>${item.name}</option>`).join('');
        if (callback && data.data.length > 0) callback(data.data[0].id);
    } catch (error) {
        console.error(`Error fetching data from ${url}:`, error);
        selectElement.innerHTML = `<option value="">Failed to load data</option>`;
    }
}

function fetchAdvertisers(selectId, campaignSelectId = null, adGroupSelectId = null) {
    fetchData('/get_advertiser', selectId, 'Loading advertisers...', (firstAdvertiserId) => campaignSelectId && fetchCampaignsByAdvertiser(firstAdvertiserId, campaignSelectId, adGroupSelectId));
    document.getElementById(selectId).addEventListener('change', (event) => {
        const advertiserId = event.target.value;
        if (advertiserId && campaignSelectId) fetchCampaignsByAdvertiser(advertiserId, campaignSelectId, adGroupSelectId);
        else if (campaignSelectId) document.getElementById(campaignSelectId).innerHTML = '<option value="">Pilih advertiser terlebih dahulu</option>';
    });
}

function fetchCampaignsByAdvertiser(advertiserId, selectId, adGroupSelectId = null) {
    fetchData(`/campaign?advertiser_id=${advertiserId}`, selectId, 'Loading campaigns...', (firstCampaignId) => adGroupSelectId && fetchAdGroupByCampaign(firstCampaignId, adGroupSelectId));
    if (adGroupSelectId) document.getElementById(selectId).addEventListener('change', (event) => {
        const campaignId = event.target.value;
        if (campaignId) fetchAdGroupByCampaign(campaignId, adGroupSelectId);
        else document.getElementById(adGroupSelectId).innerHTML = '<option value="">Pilih campaign terlebih dahulu</option>';
    });
}

function fetchAdGroupByCampaign(campaignId, selectId) {
    fetchData(`/ad_group?filtering={"campaign_ids": ["${campaignId}"]}`, selectId, 'Loading ad groups...');
}

function setupModal(modalId, contentId, fetchFunction) {
    return { open: () => openModal(modalId, contentId, fetchFunction), close: () => closeModal(modalId, contentId) };
}

const campaignModal = setupModal('campaignModal', 'campaignModalContent', () => fetchAdvertisers('advertiserSelectCampaign', 'campaignSelectCampaign'));
const adGroupModal = setupModal('adGroupModal', 'adGroupModalContent', () => fetchAdvertisers('advertiserSelectAdGroup', 'campaignSelectAdGroup'));
const adModal = setupModal('adModal', 'adModalContent', () => fetchAdvertisers('advertiserSelectAd', 'campaignSelectAd', 'adGroupSelectAd'));

document.getElementById('openCampaignModal').addEventListener('click', campaignModal.open);
document.getElementById('openAdGroupModal').addEventListener('click', adGroupModal.open);
document.getElementById('openAdModal').addEventListener('click', adModal.open);

document.getElementById('closeCampaignModal').addEventListener('click', campaignModal.close);
document.getElementById('closeAdGroupModal').addEventListener('click', adGroupModal.close);
document.getElementById('closeAdModal').addEventListener('click', adModal.close);

document.getElementById("campaignForm").addEventListener("submit", function(event) {
    event.preventDefault();
    submitForm('/campaign', { advertiser_id: document.getElementById("advertiserSelectCampaign").value, campaign_name: document.getElementById("campaignName").value.trim(), campaign_budget: document.getElementById("campaignBudget").value.trim() });
});

document.getElementById("adGroupForm").addEventListener("submit", function(event) {
    event.preventDefault();
    submitForm('/ad_group', { advertiser_id: document.getElementById("advertiserSelectAdGroup").value, campaign_id: document.getElementById("campaignSelectAdGroup").value, ad_group_name: document.getElementById("adGroupName").value.trim(), ad_group_budget: document.getElementById("adGroupBudget").value.trim() });
});

document.getElementById("adForm").addEventListener("submit", function(event) {
    event.preventDefault();
    let formData = new FormData();
    formData.append("advertiser_id", document.getElementById("advertiserSelectAd").value);
    formData.append("campaign_id", document.getElementById("campaignSelectAd").value);
    formData.append("ad_group_id", document.getElementById("adGroupSelectAd").value);
    formData.append("ad_name", document.getElementById("adName").value.trim());
    formData.append("ad_file", document.getElementById("adFile").files[0]);
    submitForm('/ad', formData, false);
});

async function submitForm(url, data, isJson = true) {
    document.getElementById("loadingOverlay").classList.remove("hidden");
    try {
        const response = await fetch(url, { method: "POST", headers: isJson ? { "Content-Type": "application/json" } : {}, body: isJson ? JSON.stringify(data) : data });
        const result = await response.json();
        alert(result.success ? "Operation successful!" : "Failed: " + result.message);
        if (result.success) {
            if (url.includes("/campaign")) { document.getElementById("campaignForm").reset();}
            else if (url.includes("/ad_group")) {document.getElementById("adGroupForm").reset();}
            else if (url.includes("/ad")) {document.getElementById("adForm").reset();}}
    } catch (error) {
        alert("Error: " + error.message);
    } finally {
        document.getElementById("loadingOverlay").classList.add("hidden");
    }
}

async function fetchDataAdvertisersReport(url, selectId, defaultText) {
    const selectElement = document.getElementById(selectId);
    selectElement.innerHTML = `<option value="">${defaultText}</option>`;
    try {
    const response = await fetch(url);
    const data = await response.json();
    if (!data?.data || !Array.isArray(data.data)) throw new Error("Invalid data format");
    selectElement.innerHTML = data.data.length === 0 ? `<option value="">No data available</option>` : data.data.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
    } catch (error) {
    console.error(`Error fetching data from ${url}:`, error);
    selectElement.innerHTML = `<option value="">Failed to load data</option>`;
    }
}

async function fetchAdvertisersReport() {
    await fetchDataAdvertisersReport('/get_advertiser', 'advertiserSelect', 'Loading advertisers...');
}

async function fetchReport() {
    document.getElementById("loadingOverlay").classList.remove("hidden");
    const advertiserId = document.getElementById('advertiserSelect').value;
    const level = document.getElementById('levelSelect').value;
    
    // const url = `/report/${level}?advertiser_id=${advertiserId}`;
    // Get date range parameters from UI
    const dateRangeType = document.getElementById('dateRangeType').value; // 'lifetime' or 'custom'
    let url = `/report/${level}?advertiser_id=${advertiserId}&date_range=${dateRangeType}`;

    // Add date parameters for custom range
    if (dateRangeType === 'custom') {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        if (startDate && endDate) {
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }
    }
    
    try {
        const response = await fetch(url);
        const data = await response.json();

        // Display date range info if available
        if (data.date_range) {
            let dateInfoText = '';
            if (data.date_range.type === 'lifetime') {
                dateInfoText = 'Showing lifetime data';
            } else if (data.date_range.type === 'custom') {
                dateInfoText = `Date range: ${data.date_range.start_date} to ${data.date_range.end_date}`;
            }
            document.getElementById('dateRangeInfo').textContent = dateInfoText;
        }
        
        renderTable(data.data, level);
    } catch (error) {
        console.error('Error fetching report data:', error);
    }finally{
        document.getElementById("loadingOverlay").classList.add("hidden");
    }
}

function renderTable(data, type) {
    const tableHead = document.getElementById('table-head');
    const tableBody = document.getElementById('table-body');
  
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
  
    let columns = [];
    if (type === 'ad') {
      columns = [
        { key: 'ad_id', label: 'Ad ID' },
        { key: 'ad_name', label: 'Ad Name' },
        { key: 'adgroup_name', label: 'Ad Group', format: (value, item) => `${value} (${item.adgroup_id})` },
        { key: 'campaign_name', label: 'Campaign', format: (value, item) => `${value} (${item.campaign_id})` },
        { key: 'clicks', label: 'Clicks' },
        { key: 'conversion', label: 'Conversions', format: (value, item) => `${value} (${item.conversion_rate}%)` },
        { key: 'ctr', label: 'CTR', format: (value) => `${value}%` },
        { key: 'cpc', label: 'CPC', format: (value) => `$${value}` },
        { key: 'impressions', label: 'Impressions' },
        { key: 'spend', label: 'Spend', format: (value) => `$${value}` },
      ];
    } else if (type === 'adgroup') {
      columns = [
        { key: 'adgroup_id', label: 'Ad Group ID' },
        { key: 'adgroup_name', label: 'Ad Group Name' },
        { key: 'campaign_name', label: 'Campaign', format: (value, item) => `${value} (${item.campaign_id})` },
        { key: 'clicks', label: 'Clicks' },
        { key: 'conversion', label: 'Conversions', format: (value, item) => `${value} (${item.conversion_rate}%)` },
        { key: 'ctr', label: 'CTR', format: (value) => `${value}%` },
        { key: 'cpc', label: 'CPC', format: (value) => `$${value}` },
        { key: 'impressions', label: 'Impressions' },
        { key: 'spend', label: 'Spend', format: (value) => `$${value}` },
      ];
    } else if (type === 'campaign') {
      columns = [
        { key: 'campaign_id', label: 'Campaign ID' },
        { key: 'campaign_name', label: 'Campaign Name' },
        { key: 'clicks', label: 'Clicks' },
        { key: 'conversion', label: 'Conversions', format: (value, item) => `${value} (${item.conversion_rate}%)` },
        { key: 'ctr', label: 'CTR', format: (value) => `${value}%` },
        { key: 'cpc', label: 'CPC', format: (value) => `$${value}` },
        { key: 'impressions', label: 'Impressions' },
        { key: 'spend', label: 'Spend', format: (value) => `$${value}` },
      ];
    }
  
    const headerRow = document.createElement('tr');
    columns.forEach(column => {
      const th = document.createElement('th');
      th.className = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
      th.textContent = column.label;
      headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
  
    data.forEach(item => {
      const row = document.createElement('tr');
      columns.forEach(column => {
        const td = document.createElement('td');
        td.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-900';
        const value = item[column.key];
        if (column.format) {
          td.innerHTML = column.format(value, item);
        } else {
          td.textContent = value;
        }
        row.appendChild(td);
      });
      tableBody.appendChild(row);
    });
  }

document.getElementById('advertiserSelect').addEventListener('change', () => {
    fetchReport();
});

document.getElementById('levelSelect').addEventListener('change', () => {
    fetchReport();
});

socket.on('token_update', data => data.access_token && (document.getElementById("tokenDisplay").innerText = data.access_token));
window.onload = async function () {
    await fetchToken();
    await fetchAdvertisersReport();
    fetchReport();
};