
export { };

declare module "store" {

  export interface Store{
    campaigns: any;
    campaigns_url: string;
    experiment_keys: any;
    experiment_objects: any;
    experiments: any;
    experiments_url: string;
    main_url: string;
    state_url: string;
    wc_info: any;
    wc_state: any;
  }
}
