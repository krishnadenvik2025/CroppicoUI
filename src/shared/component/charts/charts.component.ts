import { Component, Inject, OnInit, ViewChild } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';

import {
  ChartComponent,
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexDataLabels,
  ApexStroke,
  ApexMarkers,
  ApexYAxis,
  ApexGrid,
  ApexTitleSubtitle,
  ApexLegend
} from "ng-apexcharts";
import { ApiService } from 'src/core/api-service/api.service';
import { APIS } from 'src/shared/model/api.model';

export type ChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  stroke: ApexStroke;
  dataLabels: ApexDataLabels;
  markers: ApexMarkers;
  tooltip: any; // ApexTooltip;
  yaxis: ApexYAxis;
  grid: ApexGrid;
  legend: ApexLegend;
  title: ApexTitleSubtitle;
  toolbar: any;
};


@Component({
  selector: 'app-charts',
  templateUrl: './charts.component.html',
  styleUrls: ['./charts.component.css']
})
export class ChartsComponent implements OnInit {
  @ViewChild("chart")
  chart: ChartComponent = new ChartComponent;
  public chartOptions: Partial<ChartOptions>;

  constructor (public dialogRef: MatDialogRef<ChartComponent>,
    private apiService: ApiService,
    @Inject(MAT_DIALOG_DATA) public dialogData: any,) {
    this.chartOptions = {
      series: [],
      chart: {
        height: 330,
        type: "line",
        toolbar: {
          offsetX: 0,
          offsetY: 0,
          show: true,
          tools: {
            download: false,
            pan: false,
            selection: false,
            reset: true
          }
        }
      },

      dataLabels: {
        enabled: false
      },
      stroke: {
        width: 5,
        curve: "straight",
        dashArray: [0, 0, 0, 0]
      },
      title: {
        text: `${new Date().toDateString()}`,
        align: "left"
      },
      legend: {
        tooltipHoverFormatter: function (val, opts) {
          return (
            val +
            " - <strong>" +
            opts.w.globals.series[opts.seriesIndex][opts.dataPointIndex] +
            "</strong>"
          );
        },

      },
      markers: {
        size: 0,
        hover: {
          sizeOffset: 6
        }
      },
      xaxis: {
        labels: {
          trim: false
        },
        tickAmount: 20,
      },
      yaxis: {
        tickAmount: 13
      },
      tooltip: {
        y: [
          {
            title: {
              formatter: function (val: string) {
                return val;
              }
            }
          },
          {
            title: {
              formatter: function (val: string) {
                return val;
              }
            }
          },
          {
            title: {
              formatter: function (val: any) {
                return val;
              }
            }
          }
        ]
      },
      grid: {
        borderColor: "#f1f1f1"
      }
    };

  }

  ngOnInit (): void {
    this.initFn();
  };

  initFn = () => {

    // Get current date in local time zone
    const currentDate = new Date();
    const timeZoneOffset = currentDate.getTimezoneOffset() * 60000; // Offset in milliseconds

    // Set start time to 00:00:00
    currentDate.setHours(0, 0, 0, 0);
    const start_date = new Date(currentDate.getTime() - timeZoneOffset).toISOString().slice(0, 19).replace('T', ' ');

    // Set end time to 23:59:59.999
    currentDate.setHours(23, 59, 59, 999);
    const end_date = new Date(currentDate.getTime() - timeZoneOffset).toISOString().slice(0, 19).replace('T', ' ');

    console.log('Start Date:', start_date);
    console.log('End Date:', end_date);

    this.apiService.httpGet(`${APIS.GET_GRAPH_DATA}/${start_date.toString()}/${end_date.toString()}`).subscribe((res) => {
      if (res.data?.length) {
        const serices_data: any[] = [];
        setTimeout(() => {
          res.data.map((d: any) => {
            const sensor = ['EC', 'PH', 'water_temp', 'ambient_temp'];
            if (sensor.includes(d.name)) {
              serices_data.push(d);
            }

          });
          this.chartOptions.series = serices_data;
        });


      }

    });
  };
}
