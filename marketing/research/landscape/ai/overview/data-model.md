# Common Data Model for AI Platform Market Landscape Research

This enhanced schema structures competitive intelligence, positioning signals, and supporting evidence so cross-functional teams can interrogate the dataset consistently. Enumerations are defined for every attribute with controlled vocabularies to enforce quality and enable analytics across storage solutions (relational, document, or graph).

## Conceptual Graph

```
Vendor ──< ProductOffering ──< PricingPlan
   │             │              │
   │             ├── PositioningStatement
   │             ├── SegmentTag ── SegmentCode
   │             ├── BusinessModelLink ── BusinessModel
   │             ├── CapabilityCoverage ── Capability ── CapabilityCategory
   │             ├── EvidenceItem ── SourceArtifact ── SourceFormat
   │             └── ProductPersonaTarget ── Persona
   │
   ├── VendorIndustryFocus ── IndustryCode
   └── Relationship ── RelationshipType
```

## Entity Specifications

For each attribute the type column refers either to a primitive (`string`, `date`, `integer`, `decimal`, `uuid`, `boolean`) or to an enumeration defined in the next section.

### `Vendor`
| Field | Type | Description |
| --- | --- | --- |
| `vendor_id` | uuid | Primary key. Stable unique identifier. |
| `name` | string | Legal or commonly used company name. |
| `headquarters_region` | RegionCode | Region of headquarters. |
| `company_type` | CompanyType | Organizational archetype. |
| `founded_year` | integer | Four-digit year. |
| `employee_range` | EmployeeBand | Binned employee count. |
| `funding_stage` | FundingStage | Latest disclosed funding stage. |
| `website_url` | string | Primary marketing site. |
| `parent_company_id` | uuid (nullable) | Links to parent vendor if applicable. |
| `description` | string | Short profile (optional). |
| `tech_stack_notes` | string | Optional notes on core technology/capabilities. |

### `VendorIndustryFocus`
Captures industry specializations beyond product-level tags.
| Field | Type |
| --- | --- |
| `vendor_id` | uuid |
| `industry_code` | IndustryCode |
| `specialization_notes` | string |

### `ProductOffering`
| Field | Type | Description |
| --- | --- | --- |
| `product_id` | uuid | Primary key. |
| `vendor_id` | uuid | FK to `Vendor`. |
| `name` | string | Product/solution brand. |
| `tagline` | string | Marketed tagline. |
| `offering_type` | OfferingType | Alignment to taxonomy. |
| `deployment_model` | DeploymentModel | Primary delivery model. |
| `target_enterprise_size` | EnterpriseSize | SMB/Enterprise alignment. |
| `release_status` | ReleaseStatus | Lifecycle status. |
| `positioning_summary` | string | 1–2 sentence narrative. |
| `last_updated` | date | Date of latest intelligence review. |

### `ProductPersonaTarget`
| Field | Type |
| --- | --- |
| `product_id` | uuid |
| `persona_code` | Persona |
| `priority` | PriorityRank |

### `SegmentTag`
| Field | Type |
| --- | --- |
| `product_id` | uuid |
| `segment_code` | SegmentCode |
| `fit_score` | FitScore |
| `primary_segment` | boolean |
| `notes` | string |

### `PositioningStatement`
| Field | Type |
| --- | --- |
| `statement_id` | uuid |
| `product_id` | uuid |
| `message_theme` | MessageTheme |
| `message_text` | string |
| `audience` | Persona |
| `evidence_strength` | EvidenceStrength |
| `source_id` | uuid |
| `valid_from` | date |
| `valid_to` | date (nullable) |

### `Capability`
| Field | Type |
| --- | --- |
| `capability_id` | uuid |
| `name` | string |
| `category` | CapabilityCategory |
| `description` | string |

### `CapabilityCoverage`
| Field | Type |
| --- | --- |
| `product_id` | uuid |
| `capability_id` | uuid |
| `maturity_level` | CapabilityMaturity |
| `differentiators` | string |
| `evidence_id` | uuid (nullable) |

### `BusinessModel`
| Field | Type |
| --- | --- |
| `business_model_id` | BusinessModelCode |
| `name` | string |
| `definition` | string |
| `common_metrics` | string |
| `typical_buyers` | string |

### `BusinessModelLink`
| Field | Type |
| --- | --- |
| `product_id` | uuid |
| `business_model_id` | BusinessModelCode |
| `priority` | PriorityRank |
| `notes` | string |

### `PricingPlan`
| Field | Type |
| --- | --- |
| `plan_id` | uuid |
| `product_id` | uuid |
| `plan_name` | string |
| `billing_metric` | BillingMetric |
| `price_currency` | CurrencyCode |
| `price_amount` | decimal |
| `price_range_min` | decimal (nullable) |
| `price_range_max` | decimal (nullable) |
| `billing_frequency` | BillingFrequency |
| `plan_type` | PricingPlanType |
| `effective_date` | date |
| `expiration_date` | date (nullable) |
| `source_id` | uuid |
| `notes` | string |

### `EvidenceItem`
| Field | Type |
| --- | --- |
| `evidence_id` | uuid |
| `product_id` | uuid |
| `evidence_type` | EvidenceType |
| `summary` | string |
| `signal_strength` | EvidenceStrength |
| `source_id` | uuid |
| `recorded_by` | string |
| `recorded_at` | date |

### `SourceArtifact`
| Field | Type |
| --- | --- |
| `source_id` | uuid |
| `title` | string |
| `format` | SourceFormat |
| `url` | string |
| `publication_date` | date |
| `publisher` | string |
| `local_path` | string |
| `license` | SourceLicense |
| `credibility_score` | CredibilityScore |

### `Relationship`
| Field | Type |
| --- | --- |
| `relationship_id` | uuid |
| `vendor_id` | uuid |
| `counterparty_vendor_id` | uuid |
| `relationship_type` | RelationshipType |
| `description` | string |
| `start_date` | date |
| `end_date` | date (nullable) |
| `source_id` | uuid |

### `CustomerReference`
| Field | Type |
| --- | --- |
| `reference_id` | uuid |
| `product_id` | uuid |
| `customer_name` | string |
| `industry_code` | IndustryCode |
| `use_case` | string |
| `outcome_metrics` | string |
| `quote` | string |
| `anonymized` | boolean |
| `source_id` | uuid |

### `MarketSignal`
| Field | Type |
| --- | --- |
| `signal_id` | uuid |
| `product_id` | uuid |
| `signal_type` | MarketSignalType |
| `details` | string |
| `impact_assessment` | ImpactAssessment |
| `signal_date` | date |
| `source_id` | uuid |

## Enumerations

### `RegionCode`
| Value | Description |
| --- | --- |
| `na` | North America |
| `latam` | Latin America |
| `emea` | Europe, Middle East, Africa |
| `apac` | Asia-Pacific |
| `global` | Operates globally without clear HQ region |

### `CompanyType`
| Value | Description |
| --- | --- |
| `hyperscaler` | Large-scale cloud/infrastructure provider |
| `independent_isv` | Independent software vendor |
| `startup` | Venture-backed or early-stage company |
| `oss_foundation` | Open-source foundation or steward |
| `system_integrator` | Services-led integrator with productized IP |
| `device_manufacturer` | Hardware-first company embedding AI |
| `consultancy` | Consulting firm with managed AI platform |
| `marketplace_operator` | Platform primarily aggregating partner solutions |

### `EmployeeBand`
| Value | Range |
| --- | --- |
| `lt_50` | < 50 employees |
| `50_199` | 50–199 |
| `200_499` | 200–499 |
| `500_999` | 500–999 |
| `1k_4k` | 1,000–4,999 |
| `5k_9k` | 5,000–9,999 |
| `10k_plus` | ≥ 10,000 |

### `FundingStage`
| Value | Description |
| --- | --- |
| `bootstrapped` | No external institutional funding |
| `seed` | Seed stage |
| `series_a` | Series A |
| `series_b` | Series B |
| `series_c_plus` | Series C or later |
| `growth_equity` | Growth equity investment |
| `public` | Publicly traded |
| `corporate_backed` | Corporate venture/strategic funding |

### `OfferingType`
| Value | Description |
| --- | --- |
| `foundation_model_api` | Hosted LLM/multimodal API platform |
| `platform_suite` | Horizontal AI/ML suite or MLOps platform |
| `vertical_solution` | Industry/domain-specific AI solution |
| `functional_tool` | Workflow-specific AI application |
| `edge_platform` | Edge/embedded AI platform |
| `agentic_automation` | Multi-agent orchestration platform |
| `ecosystem_enabler` | Marketplace, data, or tooling enabler |
| `open_source_distribution` | Open-weight model/tool distribution |
| `infrastructure_cloud` | GPU/accelerator or infrastructure service |

### `DeploymentModel`
| Value | Description |
| --- | --- |
| `saas` | Multi-tenant SaaS |
| `managed_private_cloud` | Single-tenant or VPC-managed deployment |
| `on_premises` | Customer-hosted on-prem solution |
| `hybrid` | Combination of cloud and on-prem deployments |
| `edge` | Deployed on edge appliances |
| `on_device` | Runs directly on end-user devices |

### `EnterpriseSize`
| Value | Description |
| --- | --- |
| `smb` | < 1,000 employees |
| `mid_market` | 1,000–4,999 employees |
| `enterprise` | ≥ 5,000 employees |
| `all_segments` | Broadly marketed across sizes |

### `ReleaseStatus`
| Value | Description |
| --- | --- |
| `ga` | Generally available |
| `beta` | Limited/beta release |
| `pilot` | Pilot/POC-only |
| `concept` | Announced or roadmap |
| `deprecated` | No longer sold |

### `PriorityRank`
| Value | Description |
| --- | --- |
| `primary` | Core focus |
| `secondary` | Important but not primary |
| `tertiary` | Peripheral |

### `FitScore`
| Value | Description |
| --- | --- |
| `1` | Low fit |
| `2` | Partial fit |
| `3` | Moderate fit |
| `4` | Strong fit |
| `5` | Ideal fit |

### `MessageTheme`
| Value | Description |
| --- | --- |
| `trust` | Security, compliance, responsible AI |
| `scalability` | Performance, reliability |
| `productivity` | Efficiency, automation |
| `integration` | Ecosystem connectivity |
| `cost` | TCO, ROI |
| `innovation` | Cutting-edge capabilities |
| `industry_focus` | Domain-specific value |
| `time_to_value` | Speed of implementation |

### `EvidenceStrength`
| Value | Description |
| --- | --- |
| `low` | Unverified claim |
| `medium` | Backed by vendor material |
| `high` | Third-party validated |
| `very_high` | Independently audited/regulatory |

### `CapabilityCategory`
| Value | Description |
| --- | --- |
| `foundation_model_access` | Model hosting, catalog, APIs |
| `data_integration` | Pipelines, ETL, feature stores |
| `mlops_lifecycle` | Experimentation, deployment, monitoring |
| `governance_compliance` | Responsible AI, policy, audit |
| `workflow_automation` | Process automation, co-pilots |
| `edge_runtime` | On-device/edge capabilities |
| `safety_guardrails` | Moderation, policy enforcement |
| `agent_orchestration` | Multi-agent planning, tooling |
| `analytics_reporting` | Visualization, BI integration |
| `marketplace_ecosystem` | Third-party integrations, apps |

### `CapabilityMaturity`
| Value | Description |
| --- | --- |
| `nascent` | Early roadmap |
| `emerging` | Limited deployments |
| `mature` | Established and widely deployed |
| `market_leading` | Differentiated, best-in-class |

### `BusinessModelCode`
Aligns with monetization patterns in `business-models/index.md`.
| Value | Description |
| --- | --- |
| `bm_usage` | Usage-based infrastructure pricing |
| `bm_subscription` | Seat/workspace SaaS |
| `bm_outcome` | Volume/outcome based |
| `bm_enterprise_agreement` | Multi-year platform licensing |
| `bm_open_core` | Open-core & support |
| `bm_marketplace_share` | Marketplace revenue share |
| `bm_services` | Professional services/managed delivery |
| `bm_oem` | OEM/embedded licensing |
| `bm_freemium` | Freemium/developer-led |
| `bm_advertising` | Advertising/data monetization |

### `BillingMetric`
| Value | Description |
| --- | --- |
| `per_token` | Tokens consumed |
| `per_request` | API calls |
| `per_seat` | Named users |
| `per_workspace` | Workspaces or tenants |
| `per_device` | Devices/endpoints |
| `per_gpu_hour` | Compute hour |
| `per_transaction` | Business transaction |
| `per_output_asset` | Generated asset |
| `flat_fee` | Fixed recurring fee |

### `BillingFrequency`
| Value | Description |
| --- | --- |
| `hourly` | Hourly billing |
| `daily` | Daily |
| `monthly` | Monthly |
| `quarterly` | Quarterly |
| `annual` | Annually |
| `usage_event` | Event-driven/real-time |

### `PricingPlanType`
| Value | Description |
| --- | --- |
| `public_list` | Published pricing |
| `enterprise_custom` | Custom enterprise plan |
| `free_tier` | Free or trial tier |
| `bundle` | Bundled with other products |
| `usage_commitment` | Discounted committed spend |

### `CurrencyCode`
ISO 4217 three-letter codes. Maintain a controlled list (e.g., `USD`, `EUR`, `GBP`, `JPY`, `CNY`).

### `EvidenceType`
| Value | Description |
| --- | --- |
| `case_study` | Customer case |
| `press_release` | Company announcement |
| `analyst_report` | Third-party analyst |
| `regulatory_filing` | Regulatory or certification |
| `product_documentation` | Official docs |
| `media_article` | Trusted media coverage |
| `event_presentation` | Conference/webinar |
| `social_proof` | Testimonials, reviews |

### `SourceFormat`
| Value | Description |
| --- | --- |
| `pdf` | Portable Document Format |
| `html` | Web page |
| `video` | Video recording |
| `audio` | Podcast/audio |
| `image` | Slide/infographic |
| `dataset` | Downloaded data file |
| `text` | Plain text/markdown |

### `SourceLicense`
| Value | Description |
| --- | --- |
| `public` | Public domain/open |
| `copyrighted` | Standard copyright |
| `creative_commons` | Creative Commons |
| `confidential` | Internal/confidential |
| `proprietary_paid` | Licensed paid content |

### `CredibilityScore`
| Value | Description |
| --- | --- |
| `1` | Low reliability |
| `2` | Medium |
| `3` | High |
| `4` | Verified |

### `RelationshipType`
| Value | Description |
| --- | --- |
| `partnership` | Strategic or technical partnership |
| `integration` | Product integration |
| `reseller` | Reseller/distribution |
| `competitor` | Key competitor |
| `customer_supplier` | Supply chain relationship |

### `Persona`
| Value | Description |
| --- | --- |
| `cio` | Chief Information Officer |
| `cto` | Chief Technology Officer |
| `cdo` | Chief Data Officer |
| `ciso` | Chief Information Security Officer |
| `cfo` | Chief Financial Officer |
| `cmo` | Chief Marketing Officer |
| `cro` | Chief Revenue Officer |
| `coo` | Chief Operating Officer |
| `head_platform_engineering` | Platform engineering leader |
| `head_data_science` | Data science/ML leader |
| `head_risk_compliance` | Risk/compliance leader |
| `head_operations` | Operations excellence leader |
| `product_leader` | VP Product/GM |
| `innovation_lead` | Innovation/transformation lead |
| `developer` | Individual developer/engineer |
| `line_of_business_exec` | Business unit executive |

### `IndustryCode`
Adopt a controlled list aligned to the research taxonomy. Suggested top-level codes:
| Value | Description |
| --- | --- |
| `ind_healthcare` | Healthcare & Life Sciences |
| `ind_financial_services` | Financial Services & Insurance |
| `ind_public_sector` | Public Sector & Defense |
| `ind_industrial` | Industrial, Manufacturing, Energy |
| `ind_retail_consumer` | Retail & Consumer |
| `ind_technology` | Technology & Media |
| `ind_professional_services` | Professional Services |
| `ind_telecom` | Telecommunications |
| `ind_transportation` | Transportation & Logistics |
| `ind_agriculture` | Agriculture |
| `ind_education` | Education |
| `ind_cross_industry` | Cross-industry/Horizontal |

### `SegmentCode`
Map directly to dossier filenames.
| Value | Description |
| --- | --- |
| `hyperscalers` | Hyperscaler cloud AI platforms |
| `foundation_model_providers` | Foundation model & API providers |
| `enterprise_ai_suites` | Horizontal enterprise AI suites |
| `vertical_industry_platforms` | Vertical/domain AI platforms |
| `functional_specialists` | Functional/workflow specialists |
| `edge_and_embedded` | Edge & embedded AI platforms |
| `ecosystem_enablers` | Ecosystem enablers & marketplaces |
| `community_open_source` | Community & open-source distributions |
| `agentic_automation` | Agentic automation platforms |

### `MarketSignalType`
| Value | Description |
| --- | --- |
| `funding` | Financing events |
| `merger_acquisition` | M&A activity |
| `partnership` | New partnership announcement |
| `product_launch` | Product/feature release |
| `regulatory` | Regulatory development |
| `hiring` | Executive or key hires |
| `customer_win` | Major customer announcement |
| `pricing_change` | Pricing or packaging update |
| `market_exit` | Discontinuation/exit |

### `ImpactAssessment`
| Value | Description |
| --- | --- |
| `minor` | Limited impact |
| `moderate` | Noticeable impact |
| `significant` | Material impact |
| `critical` | Transforms competitive landscape |

## Sample JSON Snippet

```json
{
  "vendor": {
    "vendor_id": "ven_aws",
    "name": "Amazon Web Services",
    "headquarters_region": "na",
    "company_type": "hyperscaler",
    "founded_year": 2006,
    "employee_range": "10k_plus",
    "funding_stage": "public"
  },
  "product_offering": {
    "product_id": "pro_bedrock",
    "vendor_id": "ven_aws",
    "name": "Amazon Bedrock",
    "offering_type": "foundation_model_api",
    "deployment_model": "saas",
    "target_enterprise_size": "enterprise",
    "release_status": "ga",
    "segment_tags": [
      {"segment_code": "hyperscalers", "fit_score": 5, "primary_segment": true},
      {"segment_code": "foundation_model_providers", "fit_score": 4, "primary_segment": false}
    ],
    "personas": [
      {"persona_code": "head_platform_engineering", "priority": "primary"},
      {"persona_code": "product_leader", "priority": "secondary"}
    ],
    "capabilities": [
      {"capability_id": "cap_model_catalog", "category": "foundation_model_access", "maturity_level": "mature"},
      {"capability_id": "cap_guardrails", "category": "safety_guardrails", "maturity_level": "emerging"}
    ],
    "business_models": [
      {"business_model_id": "bm_usage", "priority": "primary"},
      {"business_model_id": "bm_enterprise_agreement", "priority": "secondary", "notes": "Discounted commit"}
    ],
    "pricing_plans": [
      {
        "plan_id": "plan_bedrock_us",
        "billing_metric": "per_token",
        "price_currency": "USD",
        "price_amount": 0.012,
        "billing_frequency": "usage_event",
        "plan_type": "public_list",
        "effective_date": "2024-05-01"
      }
    ]
  }
}
```

## Implementation Guidance

- **Validation:** Enforce enumerations during data entry (schema validation, dropdowns). Reject records with missing required fields or invalid enum values.
- **Versioning:** Track historical rows with `valid_from`/`valid_to` to analyze positioning shifts over time.
- **Source Integrity:** Require `source_id` for all qualitative assertions and pricing data. Store raw artifacts in `downloads/` with IDs matching `SourceArtifact.local_path`.
- **Extensibility:** Additional enums can be appended without breaking existing records; ensure downstream analytics refresh dimension tables accordingly.
- **Governance:** Establish review cadence to update enumerations (e.g., add new personas or segments) and communicate changes to intake forms, dashboards, and data warehouse models.
