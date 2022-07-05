import constants
import util
import otf2
import argparse
import subprocess
import os
import Events


def write_otf2_trace(fp_in, fp_out, timer_res):

    with otf2.writer.open(fp_out, timer_resolution=timer_res) as trace:
        files, functions, events, rank_count = util.get_stats_from_recorder(fp_in)
        root_node = trace.definitions.system_tree_node("root_node")
        generic_system_tree_node = trace.definitions.system_tree_node("dummy", parent=root_node)
        posix_paradigm = trace.definitions.io_paradigm(identification="POSIX",
                                                               name="POSIX I/O",
                                                               io_paradigm_class=otf2.IoParadigmClass.SERIAL,
                                                               io_paradigm_flags=otf2.IoParadigmFlag.NONE)
        mpi_paradigm = trace.definitions.io_paradigm(identification="MPI",
                                                       name="MPI I/O",
                                                       io_paradigm_class=otf2.IoParadigmClass.PARALLEL,
                                                       io_paradigm_flags=otf2.IoParadigmFlag.NONE)

        regions = {}

        io_files = {file_name: trace.definitions.io_regular_file(file_name, scope=generic_system_tree_node) for file_name in files}

        io_handles = {}
        # io_handles = {file_name: trace.definitions.io_handle(file=io_files.get(file_name),
        #                                                                         name=file_name,
        #                                                                         io_paradigm=generic_paradigm,
        #                                                                         io_handle_flags=otf2.IoHandleFlag.NONE) for file_name in files}

        location_groups = {f"rank {rank_id}": trace.definitions.location_group(f"rank {rank_id}",
                                                                               system_tree_parent=generic_system_tree_node) for rank_id in range(rank_count)}

        locations = {f"rank {rank_id}": trace.definitions.location("Master Thread", group=location_groups.get(f"rank {rank_id}")) for rank_id in range(rank_count)}
        t_start = 0

        for rank_id in range(rank_count):
            print(f"rank {rank_id}/{rank_count}")
            writer = trace.event_writer_from_location(locations.get(f"rank {rank_id}"))
            for event in sorted([e for e in events if e.rank_id == rank_id and not (e.function.startswith("__") or e.function == "MPI_Bcast")], key=lambda x: x.start_time):
                # if event.start_time > event.end_time:
                #     print("SUS:", event.function)
                #     continue

                # print(event.function, event.start_time, event.end_time, event.rank_id)
                if regions.get(event.function) is None:
                    s = "MPI I/O" if event.function.startswith("MPI") else "POSIX I/O"
                    regions[event.function] = trace.definitions.region(event.function,
                                                                       source_file=s,
                                                                       region_role=otf2.RegionRole.FILE_IO)

                writer.enter(event.get_start_time_ticks(timer_res) - t_start,
                             regions.get(event.function))

                if isinstance(event, Events.IoEvent):

                    writer.io_operation_begin(time=event.get_start_time_ticks(timer_res) - t_start,
                                              handle=io_handles.get(event.path_name),
                                              mode=otf2.IoOperationMode(event.type),
                                              operation_flags=otf2.IoOperationFlag.NONE,
                                              bytes_request=event.size,
                                              matching_id=event.level)

                    writer.io_operation_complete(time=event.get_end_time_ticks(timer_res) - t_start,
                                                 handle=io_handles.get(event.path_name),
                                                 bytes_result=event.size,
                                                 matching_id=event.level)

                if isinstance(event, Events.SeekEvent):
                    writer.io_seek(time=event.get_start_time_ticks(timer_res) - t_start,
                                   handle=io_handles.get(event.path_name),
                                   offset_request=event.offset,
                                   whence=event.whence,
                                   offset_result=event.offset)

                elif isinstance(event, Events.OpenEvent):

                    # create handle:
                    if io_handles.get(event.path_name) is None:
                        io_handles[event.path_name] = trace.definitions.io_handle(file=io_files.get(event.path_name),
                                                                                  name=event.path_name,
                                                                                  io_paradigm=posix_paradigm,
                                                                                  io_handle_flags=otf2.IoHandleFlag.NONE)

                    # append mode or not ?
                    if event.status is None:
                        sf = otf2.IoStatusFlag(0)
                    else:
                        sf = otf2.IoStatusFlag(2) if constants.check_flag(event.status, constants.O_APPEND) else otf2.IoStatusFlag(0)

                    writer.io_create_handle(time=event.get_start_time_ticks(timer_res) - t_start,
                                            handle=io_handles.get(event.path_name),
                                            mode=otf2.IoAccessMode(event.type),
                                            creation_flags=otf2.IoCreationFlag.NONE,
                                            status_flags=sf)

                elif isinstance(event, Events.CloseEvent):
                    writer.io_destroy_handle(time=event.get_start_time_ticks(timer_res) - t_start,
                                             handle=io_handles.get(event.path_name))

                writer.leave(event.get_end_time_ticks(timer_res) - t_start,
                             regions.get(event.function))


def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=str, help="file path to the darshan trace file")
    ap.add_argument("-o", "--output", type=str, help="specifies different output path, default is ./trace_out")
    ap.add_argument("-t", "--timer", type=int, help="sets timer resolution, default is 1e9")
    args = ap.parse_args()

    fp_in = args.file
    fp_out = "./trace_out" if args.output is None else args.output
    timer_res = int(1e9) if args.timer is None else args.timer

    if os.path.isdir(fp_out):
        #exit(1)
        subprocess.run(["rm", "-rf", fp_out])

    write_otf2_trace(fp_in, fp_out, timer_res)


if __name__ == '__main__':
    main()
