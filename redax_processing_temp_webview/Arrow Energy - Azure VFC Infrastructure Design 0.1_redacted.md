Arrow Energy

Azure VFC Infrastructure Design

Verba Call Recording Solution

4 March 2021

purple.telstra.com

# Contents

[Contents [0](#_Toc65751204)](#_Toc65751204)

[1. Document Control [1](#_Toc65751205)](#_Toc65751205)

[1.1 Reviewers [1](#_Toc65751206)](#_Toc65751206)

[1.2 Change Record [1](#_Toc65751207)](#_Toc65751207)

[2. Executive Summary [2](#_Toc65751208)](#_Toc65751208)

[3. Document Purpose [3](#_Toc65751209)](#_Toc65751209)

[4. Configuration Items [4](#_Toc65751210)](#_Toc65751210)

[4.1 Network [4](#_Toc65751211)](#_Toc65751211)

[4.1.1 Public IP Address [4](#_Toc65751212)](#_Toc65751212)

[4.1.2 Site-to-Site VPN [4](#_Toc65751213)](#_Toc65751213)

[4.1.3 Public DNS [4](#_Toc65751214)](#_Toc65751214)

[4.2 SSL Certificate [4](#_Toc65751215)](#_Toc65751215)

[4.3 Virtual Machines [4](#_Toc65751216)](#_Toc65751216)

[4.4 SQL Server Express [5](#_Toc65751217)](#_Toc65751217)

[4.4.1 SQL Express Limitations [5](#_Toc65751218)](#_Toc65751218)

[4.5 Active Directory [6](#_Toc65751219)](#_Toc65751219)

[4.6 Roles & Permissions [6](#_Toc65751220)](#_Toc65751220)

[4.7 Licensing [6](#_Toc65751221)](#_Toc65751221)

[5. Project Implementation [7](#_Toc65751222)](#_Toc65751222)

[6. Important Links [8](#_Toc65751223)](#_Toc65751223)

# Document Control

## Reviewers

<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 35%" />
<col style="width: 43%" />
</colgroup>
<thead>
<tr>
<th>Reviewer</th>
<th>Role</th>
<th>Email</th>
</tr>
</thead>
<tbody>
<tr>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td>Bendik Hauge</td>
<td>Principal Consultant</td>
<td><a href="mailto:bendik.hauge@purple.telstra.com">bendik.hauge@purple.telstra.com</a></td>
</tr>
</tbody>
</table>

## Change Record

<table>
<colgroup>
<col style="width: 23%" />
<col style="width: 15%" />
<col style="width: 23%" />
<col style="width: 37%" />
</colgroup>
<thead>
<tr>
<th>Date</th>
<th>Version</th>
<th>Author</th>
<th>Change Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>4 March 2021</td>
<td>0.1</td>
<td>Marco Moretti</td>
<td>Initial draft for review</td>
</tr>
</tbody>
</table>

# Executive Summary

Arrow Energy have engaged Telstra Purple to assist in developing a call recording solution that utilises the Verba call recording software. The solution is intended to capture audio recordings for approximately 5 user phone-calls initially and will be commissioned in a new Azure tenancy under Telstra CSP.

A new Microsoft 365 tenancy will be established under the CSP (Cloud Service Partner) model and subscription billing assigned to Arrow Energy. The tenancy will be managed by Telstra Purple Managed Services however the VFC recording solution will be managed by CVT Global. The Verba call recording solution design and Implementation will be carried out by CVT Global following the design and implementation of the Azure environment and required infrastructure components to support the Verba call recording application.

# Document Purpose

The purpose of this document is to set out the Azure resources and configurational items required to support the VFC call recording solution that sits on top of Azure infrastructure. It provides the high-level design for the underlying resources, specifically the network components, virtual machines, SQL instances, and related configuration items.

This document covers the Azure configuration to support the VFC solution. It does not cover the VFC solution as that will be provided by CVT Global.

# Configuration Items

## Network

### Public IP Address

The VFC server requires a public Static IP address attached to the VM provisioned in Azure. This IP address is automatically generated at the time of commissioning the VM in Azure and is unknown until this stage. Please note that an Azure Load Balancer IP address will not be used as High Availability is not in scope of this engagement.

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr>
<th>Static IP Address (Public)</th>
<th><mark>TBD</mark></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

### Site-to-Site VPN

A site-to-site VPN is required for pause/resume of live recording from recorded users’ computers. Also site-to-site VPN is needed for management tasks such as accessing recordings, data retention to on-prem NAS/SAN and SSO.

### Public DNS

Public DNS records required for the VFC solution include an \[A\] record pointing to the public IP address of the VM and also a \[CNAME\] record pointing to the FQDN of the VM which is provided by Azure when establishing the public IP address attached when commissioning the VM.

<table>
<colgroup>
<col style="width: 31%" />
<col style="width: 28%" />
<col style="width: 39%" />
</colgroup>
<thead>
<tr>
<th><strong>Purpose</strong></th>
<th><strong>DNS Record Type</strong></th>
<th><strong>Value</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td>Public IP Address</td>
<td>[A]</td>
<td><mark>TBD</mark></td>
</tr>
<tr>
<td>Default FQDN</td>
<td>Azure provided</td>
<td><mark>TBD</mark></td>
</tr>
<tr>
<td>Custom FQDN</td>
<td>[CNAME]</td>
<td>vfc.arrowenergy.com.au</td>
</tr>
</tbody>
</table>

## SSL Certificate

A publicly signed certificate is required for the virtual machines. Two common names will be configured for the certificate associated to the FQDN (Azure provided) and CNAME record of the VM. The certificate must be:

- a CSP certificate (CND/KSP certificates are not supported

- The SAN configuration of the certificate must include the VM’s FQDN and CNAME records

- A wildcard SAN certificate is supported but can result in a higher cost of purchase/renewal

- \[REDACTED LINE\]

## Virtual Machines

The Verint VFC server requires a standard\_D4\_v2 Azure VM with SQL Server 2019 Express (15.x) installed. The need for a D4\_v2 instance is due to the requirement to have SQL Server Express running on the VM rather than separately on a dedicated VM as preferred by Arrow Energy.

Specifications for the D4\_v2 instance are as follows:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr>
<th>CPU Cores</th>
<th>8</th>
</tr>
</thead>
<tbody>
<tr>
<td>Memory (GiB)</td>
<td>28</td>
</tr>
<tr>
<td>Temporary Storage (SSD): GiB</td>
<td>400</td>
</tr>
<tr>
<td>Max NICs / Network Bandwidth</td>
<td>8 / High</td>
</tr>
</tbody>
</table>

## SQL Server Express

Microsoft SQL Server 2019 Express Edition (version 15.x) will be installed the VFC application which is bundled with the VFC installer. SQL Express will be installed on a dedicated VM instance in Azure to reduce the load on the application server.

The licensed version of SQL Server 2019 is recommended for production use and where Arrow Energy later wish to scale the VFC solution to accommodate more Teams users and higher recording volume. SQL Express can always be upgraded at a later stage if necessary.

### SQL Express Limitations

It is important to understand the limitations of using the free SQL Server Express compared to a licensed version of SQL Server 2019. SQL Server 2019 Express has the following limitations:

- There is a 10GB limit on the size of the database

- There is 1 socket or 4 core limits on the CPU usage

- There is a maximum buffer pool memory (per instance) limit of 1410MB

- There is a maximum columnstore segment memory (per instance) limit of 352MB

- There is a memory-optimised data size limit (per database) of 352MB

- Log Shipping is not supported

- Database Mirror limited to Witness Only

- Backup Compression not supported

- Failover Clusters not supported

- Availability Groups not supported

- Online Page and file restore not supported

- Online Index create and rebuild not supported

- Resumable online index rebuilds not supported

- Online schema change not supported

- Fast recovery not supported

- Mirrored backups not supported

- Hot add memory and CPU not supported

- Encrypted backup not supported

- Hybrid backup to Windows Azure not supported

The above features are only available in SQL Server 2019 Enterprise edition.

## Active Directory

Azure AD and/or any hybrid connectivity to on-premises AD will not be required for the CVT solution, at least not initially. User accounts provisioned for call recording will be localised and built-in to the CVT application and managed from there.

## Roles & Permissions

The following roles and permissions are required to build and configure the Azure service fabric and to provide ongoing management and support by Telstra Purple Managed Services:

- An Azure Global Administrator (GA) user is required to build the solution and for which CVT will liaise with for configuration of the VFC application and Team recording.

- Additionally, PowerShell permissions are required by the GA for configuring Office 365 and Microsoft Teams for call recording and policies in the VFC application.

- Lastly, a Local Administrator user is required for configuring the Azure VM.

## Licensing

Users that are configured for call recording will need the following Microsoft 365 licenses:

- E3 or E5

- Phone System (Required for E3 only)

- Telstra Calling Plan / Direct Routing

# Project Implementation

The following table provides an estimation of effort in days for completing the configuration tasks and testing to ensure all services are operational:

<table>
<colgroup>
<col style="width: 69%" />
<col style="width: 30%" />
</colgroup>
<thead>
<tr>
<th>Tasks</th>
<th>Est. Effort (Days)</th>
</tr>
</thead>
<tbody>
<tr>
<td>Establish new Microsoft 365 Tenancy (CSP)</td>
<td>1 day</td>
</tr>
<tr>
<td><p>Azure tenancy and service configuration</p>
<ul>
<li><p>Commission 2x VM instances</p></li>
<li><p>Configure Public DNS</p></li>
<li><p>Assign SAN Certificate</p></li>
<li><p>Configure SQL Express</p></li>
</ul></td>
<td>3 days</td>
</tr>
<tr>
<td>Testing and compliance</td>
<td>1 days</td>
</tr>
</tbody>
</table>

# Important Links

VFC Online Administration Guide

https://kb.verba.com/display/docs/Administration+Guide
