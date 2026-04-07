export interface Sheet {
  name: string;
  page_index: number | null;
  is_paperspace: boolean;
  entity_count: number | null;
}

export interface SheetsResponse {
  sheets: Sheet[];
}

export interface UploadResponse {
  id: string;
  filename: string;
  dxf_version: string;
  layer_count: number;
  total_entities: number;
}

export interface LayerSummary {
  [layerName: string]: {
    entity_types: string[];
    entity_count: number;
  };
}

export interface Entity {
  type: string;
  text?: string;
  measurement?: number;
  block_name?: string;
  attributes?: Record<string, string>;
  insertion?: number[];
  points?: number[][];
  radius?: number;
  center?: number[];
  start?: number[];
  end?: number[];
  height?: number;
  is_closed?: boolean;
  point_count?: number;
}

export interface ExtractionResult {
  id: string;
  filename: string;
  original_filename: string;
  dxf_version: string;
  layer_count: number;
  total_entities: number;
  layers: {
    [layerName: string]: {
      entities: Entity[];
      entity_types: string[];
    };
  };
}

export interface MappingItem {
  layer: string;
  entity_type: string;
  field: string;
  column_name: string;
}

export type FieldOption = {
  value: string;
  label: string;
};

export const FIELD_OPTIONS_BY_TYPE: Record<string, FieldOption[]> = {
  TEXT: [{ value: "text", label: "Text content" }],
  MTEXT: [{ value: "text", label: "Text content" }],
  DIMENSION: [{ value: "measurement", label: "Measurement value" }],
  INSERT: [
    { value: "block_name", label: "Block name" },
    { value: "attr:ID", label: "Attribute: ID" },
    { value: "attr:TAG", label: "Attribute: TAG" },
    { value: "attr:SIZE", label: "Attribute: SIZE" },
    { value: "attr:ROOM", label: "Attribute: ROOM" },
  ],
  LWPOLYLINE: [
    { value: "area", label: "Area" },
    { value: "point_count", label: "Point count" },
  ],
  LINE: [
    { value: "start", label: "Start point" },
    { value: "end", label: "End point" },
  ],
  CIRCLE: [{ value: "radius", label: "Radius" }],
  ARC: [{ value: "radius", label: "Radius" }],
};
