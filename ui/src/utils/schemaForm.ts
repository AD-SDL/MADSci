/**
 * Utility for converting representation templates into form field descriptors.
 *
 * Takes a LocationRepresentationTemplate's schema_def, default_values, and
 * required_overrides and produces a list of FormField objects that can be
 * rendered as dynamic form inputs.
 */

export type FormFieldType = 'string' | 'number' | 'boolean' | 'json';

export interface FormFieldEnumOption {
  title: string;
  value: string | number;
}

export interface FormField {
  /** Property key in the resulting JSON object */
  key: string;
  /** Human-readable label for the form field */
  label: string;
  /** Input type to render */
  type: FormFieldType;
  /** Whether the field must be provided */
  required: boolean;
  /** Default value (may be undefined for required fields with no default) */
  defaultValue: unknown;
  /** Help text / description */
  description?: string;
  /** Enum options for string fields with restricted values */
  enumOptions?: FormFieldEnumOption[];
  /** Minimum value for number fields */
  minimum?: number;
  /** Maximum value for number fields */
  maximum?: number;
}

/**
 * Infer FormFieldType from a JavaScript value.
 */
function inferTypeFromValue(value: unknown): FormFieldType {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'string') return 'string';
  // Arrays and objects get a JSON text area
  return 'json';
}

/**
 * Map a JSON Schema type string to a FormFieldType.
 */
function mapSchemaType(schemaType: string | string[] | undefined): FormFieldType {
  const t = Array.isArray(schemaType) ? schemaType[0] : schemaType;
  switch (t) {
    case 'string':
      return 'string';
    case 'number':
    case 'integer':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'array':
    case 'object':
    default:
      return 'json';
  }
}

/**
 * Convert a representation template into a list of form field descriptors.
 *
 * Resolution order:
 * 1. If schema_def has `properties`, use those for field names, types, and descriptions
 * 2. Merge with default_values for default values
 * 3. Mark fields listed in required_overrides as required
 * 4. If no schema_def, fall back to inferring types from default_values
 * 5. Add any fields in required_overrides that aren't already present
 */
export function templateToFormFields(template: {
  default_values?: Record<string, unknown>;
  schema_def?: Record<string, unknown> | null;
  required_overrides?: string[] | null;
}): FormField[] {
  const defaults = template.default_values ?? {};
  const requiredSet = new Set(template.required_overrides ?? []);
  const fields: FormField[] = [];
  const seen = new Set<string>();

  const schema = template.schema_def as Record<string, unknown> | null | undefined;
  const properties = (schema?.properties ?? {}) as Record<string, Record<string, unknown>>;
  const hasSchema = schema != null && Object.keys(properties).length > 0;

  if (hasSchema) {
    // Build fields from schema properties
    for (const [key, propDef] of Object.entries(properties)) {
      seen.add(key);
      const fieldType = mapSchemaType(propDef.type as string | string[] | undefined);
      const field: FormField = {
        key,
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        type: fieldType,
        required: requiredSet.has(key),
        defaultValue: key in defaults ? defaults[key] : undefined,
        description: propDef.description as string | undefined,
      };

      // Handle enum options for string fields
      if (fieldType === 'string' && Array.isArray(propDef.enum)) {
        field.enumOptions = (propDef.enum as (string | number)[]).map(v => ({
          title: String(v),
          value: v,
        }));
      }

      // Handle numeric constraints
      if (fieldType === 'number') {
        if (propDef.minimum !== undefined) field.minimum = propDef.minimum as number;
        if (propDef.maximum !== undefined) field.maximum = propDef.maximum as number;
      }

      fields.push(field);
    }
  }

  // Add fields from default_values that aren't in schema
  for (const [key, value] of Object.entries(defaults)) {
    if (seen.has(key)) continue;
    seen.add(key);
    fields.push({
      key,
      label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      type: inferTypeFromValue(value),
      required: requiredSet.has(key),
      defaultValue: value,
    });
  }

  // Add required fields that aren't in schema or defaults
  for (const key of requiredSet) {
    if (seen.has(key)) continue;
    seen.add(key);
    fields.push({
      key,
      label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      type: 'string', // best guess for unknown required field
      required: true,
      defaultValue: undefined,
    });
  }

  // Sort: required fields first, then alphabetical
  fields.sort((a, b) => {
    if (a.required !== b.required) return a.required ? -1 : 1;
    return a.key.localeCompare(b.key);
  });

  return fields;
}

/**
 * Build default form values from a list of FormFields.
 * For json-type fields, the defaultValue is stored as a JSON string.
 */
export function buildDefaultValues(fields: FormField[]): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.defaultValue !== undefined) {
      values[field.key] = field.type === 'json'
        ? JSON.stringify(field.defaultValue, null, 2)
        : field.defaultValue;
    } else {
      // Initialize with type-appropriate empty values
      switch (field.type) {
        case 'string':
          values[field.key] = '';
          break;
        case 'number':
          values[field.key] = null;
          break;
        case 'boolean':
          values[field.key] = false;
          break;
        case 'json':
          values[field.key] = '';
          break;
      }
    }
  }
  return values;
}

/**
 * Collect form values into a plain object suitable for API submission.
 * Parses JSON strings back into objects for json-type fields.
 * Omits fields with empty/null values unless they are required.
 */
export function collectFormValues(
  fields: FormField[],
  values: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.key];
    if (field.type === 'json' && typeof raw === 'string' && raw.trim() !== '') {
      try {
        result[field.key] = JSON.parse(raw);
      } catch {
        result[field.key] = raw;
      }
    } else if (raw !== null && raw !== undefined && raw !== '') {
      result[field.key] = raw;
    } else if (field.required) {
      result[field.key] = raw;
    }
  }
  return result;
}

/**
 * Validate form values against required fields.
 * Returns a list of error messages (empty if valid).
 */
export function validateFormValues(
  fields: FormField[],
  values: Record<string, unknown>,
): string[] {
  const errors: string[] = [];
  for (const field of fields) {
    if (!field.required) continue;
    const val = values[field.key];
    if (val === null || val === undefined || val === '') {
      errors.push(`${field.label} is required`);
    }
    if (field.type === 'json' && typeof val === 'string' && val.trim() !== '') {
      try {
        JSON.parse(val);
      } catch {
        errors.push(`${field.label} must be valid JSON`);
      }
    }
  }
  return errors;
}
