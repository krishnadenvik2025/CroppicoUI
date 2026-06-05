import {
  ApexAxisChartSeries,
  ApexChart,
  ApexDataLabels,
  ApexMarkers,
  ApexTitleSubtitle,
  ApexFill,
  ApexYAxis,
  ApexXAxis,
  ApexTooltip,
  ApexResponsive,
  ApexAnnotations,
  ApexGrid,
  ApexNonAxisChartSeries,
  ApexPlotOptions,
  ApexLegend,
  ChartComponent
} from "ng-apexcharts";

class Apex {
  public series: ApexAxisChartSeries = [];

  public water_chart: ApexChart = {
    width:300,
    height: 350,
    type: 'radialBar',
    redrawOnParentResize: true,
    redrawOnWindowResize: true,
    stacked: true,
    stackType: "100%",
    sparkline:{
      enabled:false
    },
    animations:{
      enabled:true,
      easing:"easeinout",
      speed:0.5,
      animateGradually:{
        enabled:true,
        // delay:2
      }
    }
  }

  public water_plotOption: ApexPlotOptions = {
    radialBar: {
      startAngle: -50,
      endAngle: 180,
      hollow: {
        margin: 0,
        size: "30%",
        image:undefined
      },
      track: {
        show:true,
        startAngle: -50,
        endAngle: 180
      },
      dataLabels: {
        show: false
      }
    }
  }

  public ambient_chart: ApexChart = {
    height: 200,
    type: 'radialBar',
    redrawOnParentResize: true,
    redrawOnWindowResize: true,
    stacked: true,
    stackType: "100%",
    sparkline:{
      enabled:false
    },
    animations:{
      enabled:true,
      easing:"easeinout",
      animateGradually:{
        enabled:true
      }
    }
  }
  public ambient_plotOptions: ApexPlotOptions = {
    radialBar: {
      startAngle: -200,
      endAngle: 60,
      hollow: {
        margin: 0,
        size: "20%",
        image:undefined
      },
      track: {
        show:true,
        startAngle: -200,
        endAngle: 60
      },
      dataLabels: {
        show: false
      }
    }
  }

  public labels = ["", "", ""]

  public water_colors = ["#0336ff", "#29B6F6", "#FF3D00"]

  public ambient_colors = ["#0336ff", "#FF3D00"]

}

export {
  Apex
};


//   <!-- <circle-progress [percent]="85.8" [subtitle]="'Water Level'" [subtitleFontSize]="'12'" [radius]="50"
//   [outerStrokeWidth]="12" [innerStrokeWidth]="5" [outerStrokeColor]="'#00FFA2'" [innerStrokeColor]="'#18A572'"
//   [animation]="true" [animationDuration]="300" [toFixed]="1" [titleColor]="'#FFFF'" [titleFontSize]="'18'"
//   [titleFontWeight]="'100'" [unitsColor]="'#FFFFFF'" [units]="' %'" [unitsFontSize]="'18'"
//   [unitsFontWeight]="'100'">
// </circle-progress>
// <circle-progress [percent]="22.3" [subtitle]="'Water Temperature'" [subtitleFontSize]="'18'" [radius]="100"
//   [outerStrokeWidth]="16" [innerStrokeWidth]="8" [outerStrokeColor]="'#0058FF'" [innerStrokeColor]="'#13316B'"
//   [animation]="true" [animationDuration]="300" [toFixed]="1" [titleColor]="'#FFFF'" [titleFontSize]="'36'"
//   [titleFontWeight]="'100'" [unitsColor]="'#FFFFFF'" [units]="'°C'" [unitsFontSize]="'36'"
//   [unitsFontWeight]="'100'">
// </circle-progress>
// <circle-progress [percent]="28.3" [subtitle]="'Ambient Temperature'" [subtitleFontSize]="'12'" [radius]="75"
//   [outerStrokeWidth]="16" [innerStrokeWidth]="8" [outerStrokeColor]="'#FF6F00'" [innerStrokeColor]="'#924000'"
//   [animation]="true" [animationDuration]="300" [toFixed]="1" [titleColor]="'#FFFF'" [titleFontSize]="'32'"
//   [titleFontWeight]="'100'" [unitsColor]="'#FFFFFF'" [units]="'°C'" [unitsFontSize]="'32'"
//   [unitsFontWeight]="'100'">
// </circle-progress>
// <circle-progress [percent]="25" [subtitle]="'Humidity'" [subtitleFontSize]="'15'" [radius]="50"
//   [outerStrokeWidth]="12" [innerStrokeWidth]="5" [outerStrokeColor]="'#fefefe'" [innerStrokeColor]="'#5f5f5f'"
//   [animation]="true" [maxPercent]="50" [animationDuration]="300" [toFixed]="1" [titleColor]="'#FFFF'"
//   [titleFontSize]="'18'" [titleFontWeight]="'100'" [unitsColor]="'#FFFFFF'" [units]="' %'"
//   [unitsFontSize]="'12'" [unitsFontWeight]="'100'">
// </circle-progress> -->