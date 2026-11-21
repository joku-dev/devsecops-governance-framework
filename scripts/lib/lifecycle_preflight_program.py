"""Complete original diagnostic capture/replay CLI over explicit ports."""
class LifecyclePreflightProgram:
    def __init__(self,provider,*,argument_parser,argv):
        self.provider,self.argument_parser,self.argv=provider,argument_parser,argv
        self.description='Capture or replay diagnostic live evidence; never submit lifecycle observations.'

    def main(self):
        parser = self.argument_parser(description=self.description)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--run-id')
        mode.add_argument('--verify-bundle')
        parser.add_argument('--output-dir')
        args = parser.parse_args(self.argv)
        if args.run_id:
            if not args.output_dir:
                parser.error('--run-id requires --output-dir')
            result = self.provider.collect_preflight(args.run_id, args.output_dir)
        else:
            if args.output_dir:
                parser.error('--verify-bundle does not write an output')
            result = self.provider.replay_capture(args.verify_bundle)
        print(f"GRS-002: {result['criterion']['status']}; {len(result['checks'])} capture checks passed. Diagnostic only; lifecycle acceptance not evaluated.")
